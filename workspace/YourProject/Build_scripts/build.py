#!/usr/bin/python
#coding=utf-8

import os
import subprocess
import requests
import time
import shutil
from datetime import datetime
from optparse import OptionParser

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
                provisioning_profile=None, output_folder=None, build_method='xctool'):
        super(BuildIPA, self).__init__()
        self.build_method = build_method
        self.configuration = configuration
        self.provisioning_profile = provisioning_profile
        self.output_folder = output_folder
        self.build_params = self.getBuildParams(project, target, workspace, scheme)

    def prepare(self):
        print "Output folder for ipa ============== %s" % self.output_folder
        try:
            shutil.rmtree(self.output_folder)
        except OSError:
            pass
        finally:
            os.makedirs(self.output_folder)
        print "Install pod dependencies ============="
        cmd_shell = 'pod install --no-repo-update'
        self.runShell(cmd_shell)
        print "Update pod dependencies ============="
        cmd_shell = 'pod update --no-repo-update'
        self.runShell(cmd_shell)

    def runShell(self, cmd_shell):
        process = subprocess.Popen(cmd_shell, shell = True)
        process.wait()

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
        app_path = os.path.join(self._archive_path, "Products", "Applications", "{0}.app".format(self._app_name))
        build_products = {
            'ipa_path': self._ipa_path,
            'app_path': app_path
        }
        return build_products


def parseUploadResult(jsonResult):
    print 'post response: %s' % jsonResult
    resultCode = jsonResult['code']
    if resultCode == 0:
        print "Upload Success"
        appKey = jsonResult['data']['appKey']
        print "appDownloadPage: http://www.pgyer.com/%s" % appKey
        appQRCodeURL = jsonResult['data']['appQRCodeURL']
        return appQRCodeURL
    else:
        print "Upload Fail!"
        print "Reason: %s" % jsonResult['message']
        raise

def downloadQRCodeImage(appQRCodeURL, saveFolder):
    qr_image_file_path = os.path.join(saveFolder, 'QRCode.png')
    response = requests.get(appQRCodeURL)
    if response.status_code == 200:
        with open(qr_image_file_path, 'wb') as f:
            f.write(response.content)
    print 'save QRCode image to file: %s' % qr_image_file_path

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
    while try_times < 3:
        try:
            print "uploading ..."
            ipa_file = {'file': open(ipaPath, 'rb')}
            r = requests.post(PGYER_UPLOAD_URL,
                headers = headers,
                files = ipa_file,
                data = payload
            )
            break
        except requests.exceptions.ConnectionError:
            print "requests.exceptions.ConnectionError occured!"
            time.sleep(5)
            print "try again ..."
            try_times += 1
        except Exception as e:
            print "Exception occured: %s" % str(e)
            time.sleep(5)
            print "try again ..."
            try_times += 1
    if r.status_code == requests.codes.ok:
         result = r.json()
         appQRCodeURL = parseUploadResult(result)
         output_folder = os.path.dirname(ipaPath)
         downloadQRCodeImage(appQRCodeURL, output_folder)
    else:
        print 'HTTPError, response: %s' % r.content

def main():
    parser = OptionParser()
    parser.add_option("-w", "--workspace", default = 'Store.xcworkspace', help="Build the workspace name.xcworkspace.", metavar="name.xcworkspace")
    parser.add_option("-p", "--project", help="Build the project name.xcodeproj.", metavar="name.xcodeproj")
    parser.add_option("-s", "--scheme", default = 'StoreCI', help="Build the scheme specified by schemename. Required if building a workspace.", metavar="schemename")
    parser.add_option("-t", "--target", help="Build the target specified by targetname. Required if building a project.", metavar="targetname")
    parser.add_option("-c", "--configuration", default = 'Release', help="Specify build configuration. Default value is Release.", metavar="configuration")
    parser.add_option("-o", "--output", default = 'BuildProducts', help="specify output filename", metavar="output_filename")
    parser.add_option("-d", "--update_description", default = '', help="specify update description", metavar="update_description")

    (options, args) = parser.parse_args()

    print "options: %s, args: %s" % (options, args)
    project = options.project
    workspace = options.workspace
    target = options.target
    scheme = options.scheme
    configuration = options.configuration
    output = options.output
    update_description = options.update_description

    build_ipa = BuildIPA(
        workspace = workspace,
        scheme = scheme,
        configuration = configuration,
        provisioning_profile = PROVISIONING_PROFILE,
        output_folder = output,
        build_method = BUILD_METHOND
    )
    build_ipa.build()
    build_products = build_ipa.getBuildProducts()
    ipa_path = build_products['ipa_path']
    uploadIpaToPgyer(ipa_path, update_description)


if __name__ == '__main__':
    main()
