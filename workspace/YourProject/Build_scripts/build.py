#!/usr/bin/python
#coding=utf-8

import os
import subprocess
import requests
import time
import shutil
import re
from datetime import datetime
from optparse import OptionParser
from datetime import datetime
import plistlib

#configuration for iOS build setting
BUILD_METHOND = "xctool" # "xcodebuild"
# specify build SDK
SDK = "iphoneos"
# specify build provisioning profile
PROVISIONING_PROFILE = "***distribution1"
# configuration for pgyer
USER_KEY = "9667e5933d************540b83ed7c"
API_KEY = "d2e517468e7************e24310b65"
PGYER_UPLOAD_URL = "https://www.pgyer.com/apiv1/app/upload"


class BuildIPA(object):
    """docstring for BuildIPA"""
    def __init__(self, project=None, target=None, workspace=None, scheme=None, configuration=None, \
                provisioning_profile=None, output_folder=None, \
                plist_path=None, build_version=None, build_method='xctool'):
        super(BuildIPA, self).__init__()
        self.build_method = build_method
        self.configuration = configuration
        self.provisioning_profile = provisioning_profile
        self.output_folder = output_folder
        self.plist_path = plist_path
        self.build_version = build_version
        self.build_params = self.getBuildParams(project, target, workspace, scheme)

    def prepare(self):
        self.changeBuildVersion()
        print "Output folder for ipa ============== %s" % self.output_folder
        try:
            shutil.rmtree(self.output_folder)
        except OSError:
            pass
        finally:
            os.makedirs(self.output_folder)
        print "Update pod dependencies ============="
        cmd_shell = 'pod repo update'
        self.runShell(cmd_shell)
        print "Install pod dependencies ============="
        cmd_shell = 'pod install'
        self.runShell(cmd_shell)

    def changeBuildVersion(self):
        build_version_list = self.build_version.split('.')
        CFBundleShortVersionString = '.'.join(build_version_list[:3])
        p = plistlib.readPlist(self.plist_path)
        p['CFBundleShortVersionString'] = CFBundleShortVersionString.rstrip('.0')
        p['CFBundleVersion'] = self.build_version
        plistlib.writePlist(p, self.plist_path)

    def runShell(self, cmd_shell):
        process = subprocess.Popen(cmd_shell, shell = True)
        process.wait()
        return_code = process.returncode
        assert return_code == 0

    def getBuildParams(self, project, target, workspace, scheme):
        if project is None and workspace is None:
            exit(1)
        elif project is not None:
            build_params = '-project %s -target %s' % (project, target)
            # specify package name
            self._package_name = "{0}_{1}".format(target, self.configuration)
            self._app_name = target
        elif workspace is not None:
            build_params = '-workspace %s -scheme %s' % (workspace, scheme)
            # specify package name
            self._package_name = "{0}_{1}".format(scheme, self.configuration)
            self._app_name = scheme

        build_params += ' -sdk %s -configuration %s' % (SDK, self.configuration)
        return build_params

    def buildClean(self):
        cmd_shell = '{0} {1} clean'.format(self.build_method, self.build_params)
        print "buildClean============= {0}".format(cmd_shell)
        self.runShell(cmd_shell)

    def buildArchive(self):
        # specify output xcarchive location
        self._archive_path = "{0}/{1}.xcarchive".format(self.output_folder, self._package_name)
        cmd_shell = '{0} {1} archive -archivePath {2}'.format(self.build_method, self.build_params, self._archive_path)
        print "buildArchive============= {0}".format(cmd_shell)
        self.runShell(cmd_shell)

    def exportIPA(self):
        # specify output ipa location
        self._ipa_path = "{0}/{1}.ipa".format(self.output_folder, self._package_name)
        cmd_shell = 'xcodebuild -exportArchive -archivePath {0}'.format(self._archive_path)
        cmd_shell += ' -exportPath {0}'.format(self._ipa_path)
        cmd_shell += ' -exportFormat ipa'
        cmd_shell += ' -exportProvisioningProfile "{0}"'.format(self.provisioning_profile)
        print "buildArchive============= {0}".format(cmd_shell)
        self.runShell(cmd_shell)

    def build(self):
        self.prepare()
        self.buildClean()
        self.buildArchive()
        self.exportIPA()

    def getBuildProducts(self):
        if not os.path.isfile(self._ipa_path):
            raise Exception("Failed to create ipa file!")
        app_path = os.path.join(self._archive_path, "Products", "Applications", "{0}.app".format(self._app_name))
        build_products = {
            'ipa_path': self._ipa_path,
            'app_path': app_path
        }
        return build_products


def parseUploadResult(jsonResult):
    print 'post response: %s' % jsonResult
    resultCode = jsonResult['code']

    if resultCode != 0:
        print "Upload Fail!"
        raise Exception("Reason: %s" % jsonResult['message'])

    print "Upload Success"
    appKey = jsonResult['data']['appKey']
    appDownloadPageURL = "http://www.pgyer.com/%s" % appKey
    print "appDownloadPage: %s" % appDownloadPageURL
    return appDownloadPageURL

def uploadIpaToPgyer(ipaPath, updateDescription):
    print "Begin to upload ipa to Pgyer: %s" % ipaPath
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
            print "uploading ... %s" % datetime.now()
            ipa_file = {'file': open(ipaPath, 'rb')}
            r = requests.post(PGYER_UPLOAD_URL,
                headers = headers,
                files = ipa_file,
                data = payload
            )
            assert r.status_code == requests.codes.ok
            result = r.json()
            appDownloadPageURL = parseUploadResult(result)
            return appDownloadPageURL
        except requests.exceptions.ConnectionError:
            print "requests.exceptions.ConnectionError occured!"
            time.sleep(60)
            print "try again ... %s" % datetime.now()
            try_times += 1
        except Exception as e:
            print "Exception occured: %s" % str(e)
            time.sleep(60)
            print "try again ... %s" % datetime.now()
            try_times += 1

        if try_times >= 5:
            raise Exception("Failed to upload ipa to Pgyer, retried 5 times.")

def parseQRCodeImageUrl(appDownloadPageURL):
    try_times = 0
    while try_times < 3:
        try:
            response = requests.get(appDownloadPageURL)
            assert response.status_code == 200
            regex = '<img src=\"(.*?)\" style='
            m = re.search(regex, response.content)
            assert m is not None
            appQRCodeURL = m.group(1)
            print "appQRCodeURL: %s" % appQRCodeURL
            return appQRCodeURL
        except AssertionError:
            try_times += 1
            time.sleep(60)
            print "Can not locate QRCode image. retry ... %s" % try_times

        if try_times >= 3:
            raise Exception("Failed to locate QRCode image in download page, retried 3 times.")

def saveQRCodeImage(appDownloadPageURL, output_folder):
    appQRCodeURL = parseQRCodeImageUrl(appDownloadPageURL)
    response = requests.get(appQRCodeURL)
    qr_image_file_path = os.path.join(output_folder, 'QRCode.png')
    if response.status_code == 200:
        with open(qr_image_file_path, 'wb') as f:
            f.write(response.content)
    print 'Save QRCode image to file: %s' % qr_image_file_path

def main():
    parser = OptionParser()
    parser.add_option("-w", "--workspace", default = 'Store.xcworkspace', help="Build the workspace name.xcworkspace.", metavar="name.xcworkspace")
    parser.add_option("-p", "--project", help="Build the project name.xcodeproj.", metavar="name.xcodeproj")
    parser.add_option("-s", "--scheme", default = 'StoreCI', help="Build the scheme specified by schemename. Required if building a workspace.", metavar="schemename")
    parser.add_option("-t", "--target", help="Build the target specified by targetname. Required if building a project.", metavar="targetname")
    parser.add_option("-v", "--build_version", default = '2.6.0.1', help="Specify build version number.", metavar="build_version")
    parser.add_option("-l", "--plist_path", help="Specify build plist path.", metavar="plist_path")
    parser.add_option("-c", "--configuration", default = 'Release', help="Specify build configuration. Default value is Release.", metavar="configuration")
    parser.add_option("-o", "--output", default = 'BuildProducts', help="specify output filename", metavar="output_filename")
    parser.add_option("-d", "--update_description", default = '', help="specify update description", metavar="update_description")

    (options, args) = parser.parse_args()

    print "options: %s, args: %s" % (options, args)
    project = options.project
    workspace = options.workspace
    target = options.target
    scheme = options.scheme
    plist_path = options.plist_path
    build_version = options.build_version
    configuration = options.configuration
    output = options.output
    update_description = options.update_description

    if plist_path is None:
        plist_file_name = '%s-Info.plist' % scheme
        plist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, plist_file_name))

    build_ipa = BuildIPA(
        workspace = workspace,
        scheme = scheme,
        plist_path = plist_path,
        build_version = build_version,
        configuration = configuration,
        provisioning_profile = PROVISIONING_PROFILE,
        output_folder = output,
        build_method = BUILD_METHOND
    )
    build_ipa.build()
    build_products = build_ipa.getBuildProducts()
    ipa_path = build_products['ipa_path']
    appDownloadPageURL = uploadIpaToPgyer(ipa_path, update_description)
    output_folder = os.path.dirname(ipa_path)
    saveQRCodeImage(appDownloadPageURL, output_folder)


if __name__ == '__main__':
    main()
