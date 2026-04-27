# data-profiling

**When to use**: First step of every analysis. Establish what columns exist, their types, null rates, cardinality, and sample values before deciding on methods.

**Tools**: `load_csv`, `load_excel`, `load_json`, `load_parquet`, `list_uploaded_files`, `describe_dataframe`, `profile_column`, `value_counts`, `sample_rows`.

**Workflow**:
1. Call `describe_dataframe` on the loaded df.
2. For each column relevant to the user's question, call `profile_column`.
3. For categorical columns under consideration, call `value_counts`.

**Output**: a mental model of the data — never invent columns or values that did not appear in profiling output.
