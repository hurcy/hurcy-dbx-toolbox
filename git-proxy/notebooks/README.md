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
