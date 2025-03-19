databricks bundle deploy --var-file=schemas_data.json
databricks bundle deploy --var='schemas=[{"name": "schema1", "comment": "Comment 1"}, {"name": "schema2", "comment": "Comment 2"}]'