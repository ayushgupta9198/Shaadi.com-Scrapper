from pymongo import MongoClient
from selenium import webdriver
from bs4 import BeautifulSoup
import time,re
import urllib.parse as urlparse
import random
from utilities import download_image,upload_to_dropbox
import config
import urllib.parse as urlparse
from urllib.parse import urlencode

def get_url_id(url):
    parsed = urlparse.urlparse(url)
    return  urlparse.parse_qs(parsed.query)['profileid'][0]

def save_to_db(db,data):
    "Function to store data into db"
    try:
        print('inserting into db :', data)
        print(db.insert(data))
        data_urls = []
        for img_url in profile_data["image_urls"]:
            print("***** Downloading Image Url *****", img_url)
            file_name = download_image(img_url, path_to_save=config.images_path)
            target_file_path = config.images_path + file_name
            destination_filepath = config.drpbox_destination + file_name

            print("***** Uploading to Dropbox *****", target_file_path)
            d_link = upload_to_dropbox(target_file_path,
                                       destination_file_path=destination_filepath,
                                       access_token=config.drpbox_token)
            print("upload images url : ", d_link)
            data_urls.append(d_link)
            # profile_data["drpbox_urls"].append(d_link)
        db.update({"_id":data['_id']},
                  {"$set":{"drpbox_urls":data_urls}})

    except Exception as e:
        print("Exception in inserting into db : ",e)
        pass

def do_login(driver,email, password):
    "Function to Performing login in Shadi.com"
    driver.get("https://www.shaadi.com/registration/user/login")
    driver.find_element_by_id("email").send_keys(email)
    driver.find_element_by_id("password").send_keys(password)
    driver.find_element_by_id("sign_in").click()
    time.sleep(5)
    return driver

def make_url(url,page_no):
    "Function to make a url with page numbers"
    params = {'page':page_no}
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    final_url =urlparse.urlunparse(url_parts)
    return final_url

def get_urls_from_page(driver):
    "Function to get urls from pagesource using regex"
    driver.get("https://my.shaadi.com/search/partner?loc=top-nav")
    time.sleep(15)
    print("current_url : ", driver.current_url)
    output_urls = []
    for i in range(2,100):
        new_url = make_url(driver.current_url,str(i))
        driver.get(new_url)
        random_sleep()
        pagesource = driver.page_source
        Pagetext = BeautifulSoup(pagesource, "html").prettify()
        regex = re.compile(r'/profile\?.*?"')
        page_urls = ["https://my.shaadi.com"+i.rstrip('"') for i in re.findall(regex, Pagetext)]
        output_urls.extend(page_urls)
        random_sleep()
    print("output_urls :",output_urls)
    return output_urls

def random_sleep():
    "Function to Put Random Time Sleep"
    time.sleep(random.randint(2,10))

def get_profile_data(url,driver):
    "Function to find profile urls of the Matches"

    driver.get(url)
    random_sleep()

    outdict = {}
    outdict["_id"] = get_url_id(url=url)
    outdict["name"] = ""
    outdict["age"] = ""
    outdict["gender"] = ""
    outdict["height"] = ""
    outdict["image_urls"]=[]

    # Finding Profile Name
    try:
        name = driver.find_element_by_xpath('//*[@id="root"]/div/div/div/div[2]/div[1]/div[1]/div/div[3]/div[2]/div[2]/div[1]/div/div[1]/div[1]').text # click on name
        outdict["name"] = name
    except Exception as e:
        print("Exception in finding Name Details : ",e)
        pass

    # Finding Age Details
    try:
        meta_details = driver.find_element_by_xpath('//*[@id="root"]/div/div/div/div[2]/div[1]/div[1]/div/div[3]/div[2]/div[2]/div[1]/div/div[3]/span[1]').text # click on age
        meta_details = meta_details.split(",")
        age = meta_details[0].split()[0]
        height = meta_details[1].strip()
        outdict["age"]=age
        outdict["height"]=height
    except Exception as e:
        print("Exception in finding Age : ",e)
        pass

    # Finding Profile Image URL
    try:
        src_in = driver.find_element_by_xpath('//*[@id="root"]/div/div/div/div[2]/div[1]/div[1]/div/div[3]/div[2]/div[1]/div/div/div[1]/div')
        img_src = src_in.get_attribute('src')
        outdict['image_urls'].append(img_src)
    except Exception as e:
        print("Exception in finding image url : ",e)
        pass

    return outdict


if __name__ == '__main__':
    db = MongoClient('mongodb://localhost:27017')['face-detection-dataset']['shadi.com']
    driver = webdriver.Chrome()
    driver.maximize_window()
    email = "Ayush227316@gmail.com"
    passwd = "Ayush@123"

    driver = do_login(driver=driver,email=email,password=passwd)
    profile_urls = get_urls_from_page(driver)

    for url in profile_urls:
        profile_data = get_profile_data(url,driver)
        profile_data["gender"]="female"
        save_to_db(db, profile_data)

