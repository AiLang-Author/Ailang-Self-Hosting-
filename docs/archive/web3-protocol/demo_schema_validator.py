import json
import re

# Based on 03_WIRE_PROTOCOL.md - Section 2.2 and 2.3

def validate_event_frame(payload_str):
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        return False, f"ERROR 105 BAD_JSON: {e}"

    # 1. Check Required Keys
    required_keys = {"version", "type", "action", "seq"}
    if not required_keys.issubset(data.keys()):
        return False, f"Missing required keys. Found: {list(data.keys())}"

    # 2. Assert Constraints
    if data.get("version") != "1.0":
        return False, "ERROR 100 BAD_VERSION: Only 1.0 is supported."
    
    if data.get("type") != "event":
        return False, "Invalid type. Expected 'event'."

    action = data.get("action")
    action_pattern = re.compile(r"^(load|submit|click|change|input|focus|blur|keydown|keyup|poll|stream:(open|close)|custom:[a-z][a-z0-9_-]*)$")
    if not action_pattern.match(action):
        return False, f"Invalid action verb: '{action}'"

    seq = data.get("seq")
    if not isinstance(seq, int) or seq < 0:
        return False, "Sequence number 'seq' must be a non-negative integer."

    return True, "EVENT is valid."

def validate_update_frame(payload_str):
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        return False, f"ERROR 105 BAD_JSON: {e}"

    # 1. Check Required Keys
    required_keys = {"version", "type", "seq"}
    if not required_keys.issubset(data.keys()):
        return False, f"Missing required keys. Found: {list(data.keys())}"

    # 2. Assert Constraints
    if data.get("version") != "1.0":
        return False, "ERROR 100 BAD_VERSION: Only 1.0 is supported."
    
    if data.get("type") != "update":
        return False, "Invalid type. Expected 'update'."

    seq = data.get("seq")
    if not isinstance(seq, int) or seq < 0:
        return False, "Sequence number 'seq' must be a non-negative integer."
        
    commands = data.get("commands")
    if commands is not None:
        if not isinstance(commands, list):
            return False, "'commands' must be an array."

    return True, "UPDATE is valid."

def run_tests():
    print("--- Web 3.0 Server: Python Schema Validator ---\n")

    print("--- Testing Todo App Mock Payloads ---\n")

    todo_event = """
    {
      "version": "1.0",
      "type": "event",
      "action": "submit",
      "target": "add-form",
      "region": "todo-app",
      "payload": {
        "formData": {
          "task": "Write Web3 spec"
        }
      },
      "seq": 5
    }
    """

    todo_update = """
    {
      "version": "1.0",
      "type": "update",
      "seq": 6,
      "in_reply_to": 5,
      "region": "todo-app",
      "html": "<ul id='task-list'><li><input type='checkbox'> Write Web3 spec</li></ul>",
      "commands": [
        {"op": "text", "node": "status-toast", "content": "Task Saved!"},
        {"op": "visible", "node": "status-toast", "visible": true}
      ]
    }
    """

    print("Test 3: Todo App (Client EVENT)")
    is_valid, msg = validate_event_frame(todo_event)
    print(f"Result: {'✅ PASSED' if is_valid else '❌ FAILED'} - {msg}\n")

    print("Test 4: Todo App (Server UPDATE)")
    is_valid, msg = validate_update_frame(todo_update)
    print(f"Result: {'✅ PASSED' if is_valid else '❌ FAILED'} - {msg}\n")
    valid_event = """
    {
      "version": "1.0",
      "type": "event",
      "action": "click",
      "target": "submit-btn",
      "seq": 45
    }
    """

    invalid_event_action = """
    {
      "version": "1.0",
      "type": "event",
      "action": "hack_the_gibson", 
      "seq": 46
    }
    """

    print("Test 1: Valid EVENT Frame")
    print(f"Payload: {valid_event.strip()}")
    is_valid, msg = validate_event_frame(valid_event)
    print(f"Result: {'✅ PASSED' if is_valid else '❌ FAILED'} - {msg}\n")

    print("Test 2: Invalid EVENT Action (Not in grammar)")
    print(f"Payload: {invalid_event_action.strip()}")
    is_valid, msg = validate_event_frame(invalid_event_action)
    print(f"Result: {'✅ PASSED' if is_valid else '❌ FAILED'} - {msg}\n")


if __name__ == "__main__":
    run_tests()