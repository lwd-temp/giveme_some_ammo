# https://github.com/Hawk-Zhou
# Written by Hawk, currently a 脆鲨. 
# All rights reserved.

from datetime import datetime
from mylog import my_log,my_exception,my_hr
from thefuzz import fuzz
import html2text
import os
import requests
import json
import time
import pathlib

pseudo_cache = {}

class Weibo():
    def __init__(self) -> None:
        self.cool_down = 0.5 #sec
        self.cookie = None
        self.headers = {
            "user-agent": "Mozilla/5.0 (Linux; U; Android 4.0.2; en-us; Galaxy Nexus Build/ICL53F) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"
        }
        try:
            p = os.path.join(pathlib.Path(__file__).parent.resolve(), 
                    "weibo_config.json")
            with open(p, "r") as f:
                config = json.load(f)
                self.cookie = config['cookie']
                self.headers['cookie'] = self.cookie
                my_log(f"header loaded: {self.headers}","DEBUG")
                
        except Exception as e:
            my_exception(e,"can't load cookie from json config")

        # print(self.headers)
    
    def convert_html_to_text(self,html:str)->str:
        h = html2text.HTML2Text()
        h.single_line_break = True
        h.ignore_emphasis = True
        h.ignore_links = True
        h.ignore_tables = True
        h.images_to_alt = True
        #h.use_automatic_links = True
        h.body_width = 0
        text = h.handle(html)
        text = text.rstrip()
        text = text.replace("\\[","")
        text = text.replace("\\]","")
        return text

    def one_check_request(self, url:str, omit_cooldown = False) -> requests.Response:
        # request and check "ok":1 (and thus the parseability)
        #
        # return Response

        #my_log(f"{url}","DEBUG")
        if not omit_cooldown:
            time.sleep(self.cool_down)
        else:
            time.sleep(0.05)

        try:
            response = requests.get(
                url,
                headers = self.headers
            )
        except Exception as e:
            my_exception(e, "can't get response while requesting for user mainpage")
            return None

        try:
            parsed = response.json()
            if parsed['ok'] != 1:
                my_log(f"ok is not 1 in response request:{url}","WARN")
                return None
        except Exception as e:
            # many reasons will contribute to this
            # e.g. censorship :)
            if "h5-404" in response.content.decode():
               my_log(f"Weibo internal 404 when accessing {url}","WARN")
            else: 
               my_exception(e, "can't parse response")
            return None
        
        return response

    def parse_one_weibo(self, card:dict)->dict:
        # !!! NOTE: RETURNED text may contains HTML in case of a retweet with pic
        #receive card from response['data]['cards']
        #
        #return a dict {text:str, imgs:[str,...], rt_text:str, rg_imgs:[str,...]} or None
        try:
            if card['card_type'] != 9 and card['card_type'] != 11:
                my_log(f"card type is not 9 or 11. keys:{card.keys()}","DEBUG")
                return None
        except Exception as e:
            my_exception(e, "no attribute 'card_type' when parsing weibo card")

        if card['card_type'] == 11:
            card = card['card_group'][0]
    
        if not('mblog' in card):
            my_log(f"no 'mblog' in card:{card.keys()}","DEBUG")
            return None
        
        # text extract
        text = ''
        if 'raw_text' in card['mblog']:
            text = card['mblog']['raw_text']
        else:
            # If the text is short, that is,
            # no need for digging into "... 全文"
            # just do it quick
            # no need for one more request to extract the text
            if 'isLongText' in card['mblog'] and card['mblog']['isLongText'] == False:
                try:
                    text = card['mblog']['text']
                except:
                    my_exception(e, f"can't extract text from a weibo[isLongText = False] {str(card['mblog'])}")
            else:
                try:
                    id = card['mblog']['id']
                    response = self.one_check_request(f"https://m.weibo.cn/statuses/extend?id={id}",omit_cooldown=True)
                    parsed = response.json()
                    text = parsed['data']['longTextContent']
                except Exception as e:
                    my_exception(e, f"can't expand expandable weibo. {str(card['mblog'])}")

        # image extract
        imgs = []
        if 'pics' in card['mblog']:
            imgs = [item['large']['url'] for item in card['mblog']['pics']]

        # retweet extract
        rt_text = ''
        rt_imgs = []
        if 'retweeted_status' in card['mblog']:
            if 'raw_text' in card['mblog']['retweeted_status']:
                rt_text = card['mblog']['retweeted_status']['raw_text']
            else:
                if 'isLongText' in card['mblog']['retweeted_status'] and card['mblog']['retweeted_status']['isLongText'] == False:
                    try:
                        text = card['mblog']['retweeted_status']['text']
                    except:
                        my_exception(e, f"can't extract rt_text from a weibo[isLongText = False] {str(card['mblog'])}")
                else:
                    try:
                        id = card['mblog']['retweeted_status']['id']
                        response = self.one_check_request(f"https://m.weibo.cn/statuses/extend?id={id}")
                        parsed = response.json()
                        rt_text = parsed['data']['longTextContent']
                    except Exception as e:
                        my_exception(e, f"[RT] can't expand text from RT weibo. {str(card['mblog'])}")

            if 'pics' in card['mblog']['retweeted_status']:
                rt_imgs = [item['large']['url'] for item in card['mblog']['retweeted_status']['pics']]
        
        # datetime extract
        created = card['mblog']['created_at']
        created = datetime.strptime(created,"%a %b %d %H:%M:%S +0800 %Y")
        #Tue Feb 22 19:57:43 +0800 2022

        # itemID extract
        # DISABLED DUE TO NEW FORMAT
        # try:
        #     itemID = card['itemid'].split('_')[2]
        # except:
        #     print("err")
        #     print(card['itemid'])
        #     exit()

        text = self.convert_html_to_text(text)
        rt_text = self.convert_html_to_text(rt_text)

        result = {}
        result['text'] = text
        result['imgs'] = imgs
        result['rt_text'] = rt_text
        result['rt_imgs'] = rt_imgs
        # result['url'] = f"https://weibo.com/detail/{itemID}"

        for i in result.keys():
            if i:
                break
        else:
            my_log("Completely empty parsed dictionary for one weibo","WARN")
            return None

        result['created'] = created
        
        # print(result)
        # print()

        return result

    def is_duplicate(self, fullset:int,query, threshold=90):
        for i in fullset:
            ratio = fuzz.ratio(i,query)
            if ratio >= threshold:
                # DEBUG PRINT OUT
                # print(i)
                # print(query)
                # print(ratio)
                # input()
                return True
        return False


    def giveme_some_ammo(self,pages=1,no_dup=False,threshold=70):
        all_text = []
        for i in range(pages):
            result = []
            page = i+1
            url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q\
%3D%E5%AD%97%E8%8A%82%E8%99%9A%E6%8B%9F%E5%81%B6%E5%83%8F%E5%A5%B3%E5%9B%A2%E6%88%90%E5%91%98%E5%AE%A3%E5%B8%83%E5%81%9C%E6%92%AD\
&page_type=searchall&page={str(page)}"
            parsed = self.one_check_request(url)
            # print(parsed)
            parsed = parsed.json()
            
            for item in parsed['data']['cards']:
                r = self.parse_one_weibo(item)
                if r and r['text']:
                    if no_dup:
                        if not self.is_duplicate(all_text,r['text'],threshold):
                            all_text.append(r['text'])
                            result.append(r)
                    else:
                        all_text.append(r['text'])
                        result.append(r)

            print("-----")
            for index,i in enumerate(result):
                print(index,i['text'])
                print("-----")
            
            input(f"Displayed {page}/{pages} page(s).\nPress any key to continue...")
        
if __name__ == "__main__":
    w = Weibo()
    THRESHOLD = 70
    pages = input("How many pages do you want me to fetch? (typ. value=3)\n")
    pages = int(pages)
    dup = input("Do you want duplicated text? (Y/N)\n")
    if dup == "Y":
        dup = True
    else:
        dup = False
    w.giveme_some_ammo(pages, (not dup), THRESHOLD)