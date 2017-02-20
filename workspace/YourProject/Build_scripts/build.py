#coding=utf-8
from __future__ import print_function
import os
import sys
import argparse
from ios_builder import iOSBuilder
from pgyer_uploader import uploadIpaToPgyer
from pgyer_uploader import saveQRCodeImage

def parse_args():
    parser = argparse.ArgumentParser(description='iOS app build script.')

    parser.add_argument('--build_method', dest="build_method", default='xcodebuild',
                        help="Specify build method, xctool or xcodebuild.")
    parser.add_argument('--workspace', dest="workspace", default=None,
                        help="Build the workspace name.xcworkspace")
    parser.add_argument("--scheme", dest="scheme", default=None,
                        help="Build the scheme specified by schemename. \
                        Required if building a workspace")
    parser.add_argument("--project", dest="project", default=None,
                        help="Build the project name.xcodeproj")
    parser.add_argument("--target", dest="target", default=None,
                        help="Build the target specified by targetname. \
                        Required if building a project")
    parser.add_argument("--sdk", dest="sdk", default='iphoneos',
                        help="Specify build SDK, iphoneos or iphonesimulator, \
                        default is iphonesimulator")
    parser.add_argument("--build_version", dest="build_version", default='1.0.0.1',
                        help="Specify build version number")
    parser.add_argument("--provisioning_profile", dest="provisioning_profile", default=None,
                        help="specify provisioning profile")
    parser.add_argument("--plist_path", dest="plist_path", default=None,
                        help="Specify build plist path")
    parser.add_argument("--configuration", dest="configuration", default='Release',
                        help="Specify build configuration, Release or Debug, \
                        default value is Release")
    parser.add_argument("--output_folder", dest="output_folder", default='BuildProducts',
                        help="specify output_folder folder name")
    parser.add_argument("--update_description", dest="update_description",
                        help="specify update description")

    args = parser.parse_args()
    print("args: {}".format(args))
    return args

def main():
    args = parse_args()

    if args.plist_path is None:
        plist_file_name = '%s-Info.plist' % args.scheme
        args.plist_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         os.path.pardir,
                         plist_file_name
                        )
        )

    ios_builder = iOSBuilder(args)

    if args.sdk.startswith("iphonesimulator"):
        app_zip_path = ios_builder.build_app()
        print("app_zip_path: {}".format(app_zip_path))
        sys.exit(0)

    ipa_path = ios_builder.build_ipa()
    app_download_page_url = uploadIpaToPgyer(ipa_path, args.update_description)
    try:
        output_folder = os.path.dirname(ipa_path)
        saveQRCodeImage(app_download_page_url, output_folder)
    except Exception as e:
        print("Exception occured: {}".format(str(e)))


if __name__ == '__main__':
    main()
