# Databricks Repos Proxy Enablement

## Issues

### check system's bash file
```
# which bash
/usr/bin/bash
```

### check CR LF in bash file

```
/usr/bin/bash^M: bad interpreter: No such file or directory
```
The reason might be that you saved the file on Windows, with CR LF as the line ending (\r\n).

```
sed -i -e 's/\r$//' init_scm_ca.sh
```

or try running dos2unix on the script:

http://dos2unix.sourceforge.net/

### Get pem with openssl
Now we’re approaching the less good options. It’s way better to get the CA certificates via other means than from the actual site you’re trying to connect to!

This method uses the openssl command line tool. The servername option used below is there to set the SNI field, which often is necessary to tell the server which actual site’s certificate you want.

```
$ echo quit | openssl s_client -showcerts -servername server -connect server:443 > cacert.pem
```
A real world example, getting the certs for daniel.haxx.se and then getting the main page with curl using them:

```
$ echo quit | openssl s_client -showcerts -servername daniel.haxx.se -connect daniel.haxx.se:443 > cacert.pem

$ curl --cacert cacert.pem https://daniel.haxx.se
```

convert pem to crt

```
openssl x509 -inform PEM -in fullchain.pem -out daniel.haxx.se.crt
```
