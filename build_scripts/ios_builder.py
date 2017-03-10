#coding=utf-8
from __future__ import print_function
import os
import subprocess
import shutil
import plistlib

class iOSBuilder(object):
    """docstring for iOSBuilder"""
    def __init__(self, options):
        self._build_method = options.build_method
        self._sdk = options.sdk
        self._configuration = options.configuration
        self._provisioning_profile = options.provisioning_profile
        self._output_folder = options.output_folder
        self._plist_path = options.plist_path
        self._build_version = options.build_version
        self._archive_path = None
        self._build_params = self._get_build_params(
            options.project, options.target, options.workspace, options.scheme)
        self._prepare()

    def _prepare(self):
        """ get prepared for building.
        """
        self._change_build_version()

        print("Output folder for ipa ============== {}".format(self._output_folder))
        try:
            shutil.rmtree(self._output_folder)
        except OSError:
            pass
        finally:
            os.makedirs(self._output_folder)

        self._udpate_pod_dependencies()
        self._build_clean()

    def _udpate_pod_dependencies(self):
        podfile = os.path.join(os.getcwd(), 'Podfile')
        podfile_lock = os.path.join(os.getcwd(), 'Podfile.lock')
        if os.path.isfile(podfile) or os.path.isfile(podfile_lock):
            print("Update pod dependencies =============")
            cmd_shell = 'pod repo update'
            self._run_shell(cmd_shell)
            print("Install pod dependencies =============")
            cmd_shell = 'pod install'
            self._run_shell(cmd_shell)

    def _change_build_version(self):
        """ set CFBundleVersion and CFBundleShortVersionString.
        """
        build_version_list = self._build_version.split('.')
        cf_bundle_short_version_string = '.'.join(build_version_list[:3])
        with open(self._plist_path, 'rb') as fp:
            plist_content = plistlib.load(fp)
            plist_content['CFBundleShortVersionString'] = cf_bundle_short_version_string
            plist_content['CFBundleVersion'] = self._build_version
        with open(self._plist_path, 'wb') as fp:
            plistlib.dump(plist_content, fp)

    def _run_shell(self, cmd_shell):
        process = subprocess.Popen(cmd_shell, shell=True)
        process.wait()
        return_code = process.returncode
        assert return_code == 0

    def _get_build_params(self, project, target, workspace, scheme):
        if project is None and workspace is None:
            raise "project and workspace should not both be None."
        elif project is not None:
            build_params = '-project %s -scheme %s' % (project, scheme)
            # specify package name
            self._package_name = "{0}_{1}".format(scheme, self._configuration)
            self._app_name = scheme
        elif workspace is not None:
            build_params = '-workspace %s -scheme %s' % (workspace, scheme)
            # specify package name
            self._package_name = "{0}_{1}".format(scheme, self._configuration)
            self._app_name = scheme

        build_params += ' -sdk %s -configuration %s' % (self._sdk, self._configuration)
        return build_params

    def _build_clean(self):
        cmd_shell = '{0} {1} clean'.format(self._build_method, self._build_params)
        print("build clean ============= {}".format(cmd_shell))
        self._run_shell(cmd_shell)

    def _build_archive(self):
        """ specify output xcarchive location
        """
        self._archive_path = os.path.join(
            self._output_folder, "{}.xcarchive".format(self._package_name))
        cmd_shell = '{0} {1} archive -archivePath {2}'.format(
            self._build_method, self._build_params, self._archive_path)
        print("build archive ============= {}".format(cmd_shell))
        self._run_shell(cmd_shell)

    def _export_ipa(self):
        """ export archive to ipa file, return ipa location
        """
        if self._provisioning_profile is None:
            raise "provisioning profile should not be None!"
        ipa_path = os.path.join(self._output_folder, "{}.ipa".format(self._package_name))
        cmd_shell = 'xcodebuild -exportArchive -archivePath {}'.format(self._archive_path)
        cmd_shell += ' -exportPath {}'.format(ipa_path)
        cmd_shell += ' -exportFormat ipa'
        cmd_shell += ' -exportProvisioningProfile "{}"'.format(self._provisioning_profile)
        print("build archive ============= {}".format(cmd_shell))
        self._run_shell(cmd_shell)
        return ipa_path

    def build_ipa(self):
        """ build ipa file for iOS device
        """
        self._build_archive()
        ipa_path = self._export_ipa()
        return ipa_path

    def _build_archive_for_simulator(self):
        cmd_shell = '{0} {1} -derivedDataPath {2}'.format(
            self._build_method, self._build_params, self._output_folder)
        print("build archive for simulator ============= {}".format(cmd_shell))
        self._run_shell(cmd_shell)

    def _archive_app_to_zip(self):
        app_path = os.path.join(
            self._output_folder,
            "Build",
            "Products",
            "{0}-iphonesimulator".format(self._configuration),
            "{0}.app".format(self._app_name)
        )
        app_zip_filename = os.path.basename(app_path) + ".zip"
        app_zip_path = os.path.join(self._output_folder, app_zip_filename)
        cmd_shell = "zip -r {0} {1}".format(app_zip_path, app_path)
        self._run_shell(cmd_shell)
        print("app_zip_path: %s" % app_zip_path)
        return app_zip_path

    def build_app(self):
        """ build app file for iOS simulator
        """
        self._build_archive_for_simulator()
        app_zip_path = self._archive_app_to_zip()
        return app_zip_path
