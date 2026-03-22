# TEMPLATE - Written by QA Aggregator after each QA round
# Implementation Agent reads this file in fix mode
# CRITICAL: Only modify files, functions, and lines explicitly listed here
round: 0
all_clear: false  # Set to true ONLY when fixes array is empty and all QA rounds passed
fixes:
  - id: "FIX-001"
    severity: "CRITICAL"  # CRITICAL | WARNING | INFO
    file: ""
    function: ""  # Function name, or "module-level" if fix applies outside any function
    lines: []  # List of integers, e.g., [42, 43, 44]
    instruction: ""
    reason: ""
    prohibited_scope: "Do not modify any other functions or files"
    source: ""  # security | quality | test
