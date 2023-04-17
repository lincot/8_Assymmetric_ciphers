import pexpect


def main():
    p = pexpect.spawn('python src/client.py')
    p.expect('server host.*:')
    p.sendline('')
    p.expect('server port.*:')
    p.sendline('')
    p.expect('connected to 127.0.0.1:.*')
    p.expect('connected to new port .*')
    p.expect('session token.*')
    p.sendline('')
    p.expect('username:')
    p.sendline('admin')
    p.expect('password:')
    p.sendline('supersecretadminpassword37868128593')
    p.expect('hello admin')
    p.expect('your new session token is .+')
    p.expect('> ')
    p.close()


if __name__ == '__main__':
    main()
