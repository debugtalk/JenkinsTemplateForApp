#coding=utf-8
from __future__ import print_function
import os
import requests
import time
import re
from datetime import datetime

# configuration for pgyer
USER_KEY = "9667e5933d************540b83ed7c"
API_KEY = "d2e517468e7************e24310b65"
PGYER_UPLOAD_URL = "https://www.pgyer.com/apiv1/app/upload"


def parseUploadResult(jsonResult):
    print('post response: %s' % jsonResult)
    resultCode = jsonResult['code']

    if resultCode != 0:
        print("Upload Fail!")
        raise Exception("Reason: %s" % jsonResult['message'])

    print("Upload Success")
    appKey = jsonResult['data']['appKey']
    app_download_page_url = "https://www.pgyer.com/%s" % appKey
    print("appDownloadPage: %s" % app_download_page_url)
    return app_download_page_url

def uploadIpaToPgyer(ipaPath, updateDescription):
    print("Begin to upload ipa to Pgyer: %s" % ipaPath)
    headers = {'enctype': 'multipart/form-data'}
    payload = {
        'uKey': USER_KEY,
        '_api_key': API_KEY,
        'publishRange': '2', # 直接发布
        'isPublishToPublic': '2', # 不发布到广场
        'updateDescription': updateDescription  # 版本更新描述
    }

    try_times = 0
    while try_times < 5:
        try:
            print("uploading ... %s" % datetime.now())
            ipa_file = {'file': open(ipaPath, 'rb')}
            resp = requests.post(PGYER_UPLOAD_URL, headers=headers, files=ipa_file, data=payload)
            assert resp.status_code == requests.codes.ok
            result = resp.json()
            app_download_page_url = parseUploadResult(result)
            return app_download_page_url
        except requests.exceptions.ConnectionError:
            print("requests.exceptions.ConnectionError occured!")
            time.sleep(60)
            print("try again ... %s" % datetime.now())
            try_times += 1
        except Exception as e:
            print("Exception occured: %s" % str(e))
            time.sleep(60)
            print("try again ... %s" % datetime.now())
            try_times += 1

        if try_times >= 5:
            raise Exception("Failed to upload ipa to Pgyer, retried 5 times.")

def parseQRCodeImageUrl(app_download_page_url):
    try_times = 0
    while try_times < 3:
        try:
            response = requests.get(app_download_page_url)
            regex = '<img src=\"(.*?)\" style='
            m = re.search(regex, response.content)
            assert m is not None
            appQRCodeURL = m.group(1)
            print("appQRCodeURL: %s" % appQRCodeURL)
            return appQRCodeURL
        except AssertionError:
            try_times += 1
            time.sleep(60)
            print("Can not locate QRCode image. retry ... %s: %s" % (try_times, datetime.now()))

        if try_times >= 3:
            raise Exception("Failed to locate QRCode image in download page, retried 3 times.")

def saveQRCodeImage(app_download_page_url, output_folder):
    appQRCodeURL = parseQRCodeImageUrl(app_download_page_url)
    response = requests.get(appQRCodeURL)
    qr_image_file_path = os.path.join(output_folder, 'QRCode.png')
    if response.status_code == 200:
        with open(qr_image_file_path, 'wb') as f:
            f.write(response.content)
    print('Save QRCode image to file: %s' % qr_image_file_path)
