#!/usr/bin/python
#coding=utf-8

import os
import subprocess
import shutil
import plistlib

class iOSBuilder(object):
    """docstring for iOSBuilder"""
    def __init__(self, build_method=None, workspace=None, scheme=None, project=None, target=None, \
                sdk=None, configuration=None, provisioning_profile=None, output_folder=None, \
                plist_path=None, build_version=None):
        super(iOSBuilder, self).__init__()
        self.build_method = build_method
        self.sdk = sdk
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

        build_params += ' -sdk %s -configuration %s' % (self.sdk, self.configuration)
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
        ipa_path = "{0}/{1}.ipa".format(self.output_folder, self._package_name)
        cmd_shell = 'xcodebuild -exportArchive -archivePath {0}'.format(self._archive_path)
        cmd_shell += ' -exportPath {0}'.format(ipa_path)
        cmd_shell += ' -exportFormat ipa'
        cmd_shell += ' -exportProvisioningProfile "{0}"'.format(self.provisioning_profile)
        print "buildArchive============= {0}".format(cmd_shell)
        self.runShell(cmd_shell)
        return ipa_path

    def build_ipa(self):
        self.prepare()
        self.buildClean()
        self.buildArchive()
        ipa_path = self.exportIPA()
        return ipa_path

    def buildArchiveForSimulator(self):
        cmd_shell = '{0} {1} -derivedDataPath {2}'.format(self.build_method, self.build_params, self.output_folder)
        print "buildArchiveForSimulator============= {0}".format(cmd_shell)
        self.runShell(cmd_shell)

    def archiveAppToZip(self):
        app_path = os.path.join(self.output_folder, "Build", "Products", "{0}-iphonesimulator".format(self.configuration), "{0}.app".format(self._app_name))
        app_zip_filename = os.path.basename(app_path) + ".zip"
        app_zip_path = os.path.join(self.output_folder, app_zip_filename)
        cmd_shell = "zip -r {0} {1}".format(app_zip_path, app_path)
        self.runShell(cmd_shell)
        print "app_zip_path: %s" % app_zip_path
        return app_zip_path

    def build_app(self):
        self.prepare()
        self.buildClean()
        self.buildArchiveForSimulator()
        app_zip_path = self.archiveAppToZip()
        return app_zip_path
