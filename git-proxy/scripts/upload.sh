#!/bin/bash
databricks catalogs create main --storage-root s3://hurcy-rootbucket/main
databricks schemas create default main
databricks volumes create main default scripts MANAGED
databricks fs cp init_scm_ca.sh dbfs:/Volumes/main/default/scripts/
