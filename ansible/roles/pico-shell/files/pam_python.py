"""
Set cgroup limits per user (and for all users collectively) each time a session
is opened.

Use the existing cgroups created by systemd which already map every process
into a hierarchy.  To do this, execute:
`systemctl set-property <slice> [properties...]`

See the systemd resource-control man page for available properties, and note
that they change between Ubuntu 16.04 and 18.04

Notes:

* In later versions of systemd the user-.slice template may be helpful and
  eliminate much of this code (though maybe not all).
* I've read that systemd removes the user.slice when no more users are logged
  in, so be careful making what should be persistent changes in some way
  outside of the pam stack.
* This should cover *most* processes a user creates.  Notably, cron jobs run in
  a scope outside of the user.slice so
  those processes would NOT be affected.  And, `systemd --user` procesess run
  within the user-{uid}.slice and ARE affected.
* Should work with Python 2 & 3


Installation:

0. install libpam-python
   >> apt-get install libpam-python
1. copy this file to /lib/security/pam_python.py
   >> cp pam_session.py /lib/security/
2. modify file(s) /etc/pam.d/
   >> echo "session [success=ok default=bad] pam_python.so pam_python.py" >> /etc/pam.d/sshd
3. modify auth to also use pam_python.py

"""
import os
import pwd
import syslog
import subprocess
import grp
import json
import pwd
import time
from os.path import join



pamh = None

HACKSPORTS_ROOT = "/opt/hacksports/"
COMPETITORS_GROUP = "competitors"

config_file = join(HACKSPORTS_ROOT, "config.json")
config = json.loads(open(config_file).read())
SERVER = config["web_server"]
TIMEOUT = 5

DEFAULT_USER = "nobody"

def display(string):
    message = pamh.Message(pamh.PAM_TEXT_INFO, string)
    pamh.conversation(message)


def pam_sm_open_session(_pamh, flags, argv):
    global pamh
    pamh = _pamh

    syslog.syslog(syslog.LOG_INFO, "pam_session.py: pam_sm_open_session")
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS

def competition_active():
    return True
    #r = requests.get(SERVER + "/api/user/status")
    #return json.loads(r.text)["data"]["competition_active"]


def run_login(user, password):
    r=subprocess.check_output(['/usr/bin/curl','--data','username='+user,'--data','password='+password,SERVER+"/api/user/login"])
    #return "Incorrect password"
    #r = requests.post(
    #    SERVER + "/api/user/login",
    #    data={
    #        "username": user,
    #        "password": password
    #    },
    #    timeout=TIMEOUT)
    r2=str(json.loads(r)['message'])
    return r2


def display(string):
    message = pamh.Message(pamh.PAM_TEXT_INFO, string)
    pamh.conversation(message)


def prompt(string):
    message = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, string)
    return pamh.conversation(message)


def server_user_exists(user):
    if not competition_active():
        return False
    result = run_login(user, "zzzz")
    return result == "Incorrect password"


def secure_user(user):
    home = pwd.getpwnam(user).pw_dir

    # Append only bash history
    subprocess.check_output(['touch', os.path.join(home, '.bash_history')])
    subprocess.check_output(
        ['chown', 'root:' + user,
         os.path.join(home, '.bash_history')])
    subprocess.check_output(
        ['chmod', '660', os.path.join(home, '.bash_history')])
    subprocess.check_output(
        ['chattr', '+a', os.path.join(home, '.bash_history')])

    # Secure bashrc
    subprocess.check_output([
        'cp', '/opt/hacksports/config/securebashrc',
        os.path.join(home, '.bashrc')
    ])
    subprocess.check_output(
        ['chown', 'root:' + user,
         os.path.join(home, '.bashrc')])
    subprocess.check_output(['chmod', '755', os.path.join(home, '.bashrc')])
    subprocess.check_output(['chattr', '+a', os.path.join(home, '.bashrc')])

    # Secure profile
    subprocess.check_output(
        ['chown', 'root:' + user,
         os.path.join(home, '.profile')])
    subprocess.check_output(['chmod', '755', os.path.join(home, '.profile')])
    subprocess.check_output(['chattr', '+a', os.path.join(home, '.profile')])

    # User should not own their home directory
    subprocess.check_output(["chown", "root:" + user, home])
    subprocess.check_output(["chmod", "1770", home])


def pam_sm_authenticate(pam_handle, flags, argv):
    global pamh
    pamh = pam_handle

    try:
        user = pamh.get_user(None)
    except (pamh.exception, e):
        return e.pam_result

    try:
        entry = pwd.getpwnam(user)
        group = grp.getgrnam(COMPETITORS_GROUP)
        # local account exists and server account exists
        if server_user_exists(user) and user in group.gr_mem:
            response = prompt("Enter your platform password: ")
            result = run_login(user, response.resp)

            if "Successfully logged in" in result:
                return pamh.PAM_SUCCESS
        else:
            display("unknown")
            return pamh.PAM_USER_UNKNOWN

    # local user account does not exist
    except KeyError as e:
        try:
            if server_user_exists(user):
                subprocess.check_output([
                    "/usr/sbin/useradd", "-m", "-G", COMPETITORS_GROUP, "-s",
                    "/bin/bash", user
                ])
                secure_user(user)

                display("Welcome {}!".format(user))
                display("Your shell server account has been created.")
                prompt("Please press enter and reconnect.")

                # this causes the connection to close
                return pamh.PAM_SUCCESS
            else:
                # sleep before displaying error message to slow down scanners
                time.sleep(3)
                display("Competition has not started or username does not exist on the platform website.")
                return pamh.PAM_USER_UNKNOWN

        except Exception as e:
            pass

    # sleep before failing to slow down scanners
    time.sleep(3)
    return pamh.PAM_AUTH_ERR
