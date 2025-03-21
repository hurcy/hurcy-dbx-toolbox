# Pipeline with a dedicated Unity Catalog schema

This example demonstrates how to define a Unity Catalog schema and a Delta Live Tables pipeline that uses it.

## Prerequisites

* Databricks CLI v0.244.0 or above

## Usage

databricks bundle deploy --target dev
databricks bundle deploy --var="name_prefix=" --target prd