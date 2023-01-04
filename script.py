import requests as req
from bs4 import BeautifulSoup
from dataclasses import dataclass,field
from vimeo_downloader import Vimeo
from pathlib import Path
from typing import List
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator
import re

BASE_DIR = Path(__file__).parent
EMAIL_REG = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
BASE_LINK = 'https://5quartersedu.com'
login_page = '/lms-login'


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://5quartersedu.com',
    'Connection': 'keep-alive',
    'Referer': 'https://5quartersedu.com/lms-login',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'DNT': '1',
}

@dataclass()
class Lecture:
    title:str
    link:str
    parent:'Course'
    player_link:str|None = field(default=None)
    
    
    @property
    def save_dir(self):
        return BASE_DIR / self.parent.title
        

    def download(self):
        soup_ = soup(session.get(self.link).text)
        self.player_link = soup_.find('div',class_='video_frames').find('iframe').get('src')
        
        if not self.save_dir.exists():
            self.save_dir.mkdir()
        video = Vimeo(self.player_link,embedded_on=self.link)
        video.best_stream.download(self.save_dir)
        
  
@dataclass()
class Course:
    title:str
    author:str
    link:str
    
    def process_lecture(self,lecture:BeautifulSoup):
        title_ = lecture.find_all('a')[1]
        link = title_.get('href')
        title:str =title_.text.strip()
        return Lecture(title=title,link=link,parent=self)
    
    @property
    def lectures(self)->List[Lecture]:
        soup_ = soup(session.get(self.link).text)
        lectures = soup_.find('ul',class_='lectures_lists').find_all('li')
        
        return [self.process_lecture(l) for l in lectures]

session = req.session()

def soup(data:str)->BeautifulSoup:
    return BeautifulSoup(data,'html.parser')


def login(email:str,password:str):
    re = session.get(BASE_LINK + login_page)
    token = soup(re.text).find('input',{'type':"hidden",'name':"_token"}).get('value')
    data = {'login': '','_token': token,'email': email,'password': password}
    response = session.post('https://5quartersedu.com/Login-str',data=data)
    login_tag = soup(response.content).find('input',{'type':'hidden','name':'login'})
    if login_tag:
        raise Exception('Failed to login,check your email or password')


def extract_course_data(block:BeautifulSoup)->Course:
    link_ = block.find('h4',class_='bl-title').find('a')
    link = link_.get('href')
    title = link_.text
    author = block.select_one('div.education_block_author h5 a').text
    return Course(title=title,author=author,link=link)
    
def get_subscribed_courses():
    URL = BASE_LINK + '/All-Student-Courses'
    soup_ = soup(session.get(URL).text)
    blocks = soup_.find_all('div',class_='education_block_grid')
    courses = [extract_course_data(block) for block in blocks]
    return courses

def select_course(cources:List[Course])->Course:
    selected = None
    while not selected:
        out = []
        for i,c in enumerate(cources):
            out.append(f'[{i}]{c.title}| by {c.author}')
        print('\n'.join(out),end='\n')
        selection=input('select cource: ')
        if selection and selection.isdigit():
            s = int(selection)
            if s <= len(cources) and s >= 0:
                selected = cources[s]
    return selected

def validate_email(text:str):
    return EMAIL_REG.match(text)

def main():
    email = prompt('enter email address:',validator=Validator.from_callable(validate_email),validate_while_typing=True)
    password = prompt('enter password:',is_password=True)

    if email and password:
        print('[*] logging in ....',end='\r')
        login(email,password)


    # r = session.get('https://5quartersedu.com/Profile-Student')
    cs = get_subscribed_courses()
    
    if cs:
        selected_cource = select_course(cs)
        if select_course:
            print(f'[*] processing {selected_cource.title}')
            lectures = selected_cource.lectures
            for lecture in lectures:
                print(f'[*] downloading:{lecture.title}')
                lecture.download()  
    else:
        print('[*] it seems that you do not have any subscriptions')
        print('[*] quitting....')
        exit()

def print_art():
    print(f"""
          
          simple script to download courses from {BASE_LINK}
          
          """)


if __name__ == '__main__':
    print_art()
    try:
        
        main()
    except KeyboardInterrupt as e:
        print('[*] exited by the user..')
        exit()