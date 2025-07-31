# Test script to verify the callback data parsing logic

# Статусы заявок
STATUSES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
    "rejected": "Отклонена"
}

def test_callback_parsing(callback_data, expected_status_key, expected_user_id):
    """
    Test the callback data parsing logic
    """
    print(f"Testing callback data: {callback_data}")
    
    if not callback_data.startswith("my_status_"):
        print("Error: Invalid data format")
        return False
        
    remaining_data = callback_data[len("my_status_"):]
    
    status_key = None
    user_id = None
    
    for key in STATUSES.keys():
        if remaining_data.startswith(key + "_"):
            status_key = key
            user_id = remaining_data[len(key) + 1:]
            break
    
    if not status_key or not user_id:
        print("Error: Could not extract status key or user ID")
        return False
    
    status_value = STATUSES.get(status_key)
    if not status_value:
        print(f"Error: Unknown status key: {status_key}")
        return False
    
    result = (status_key == expected_status_key and user_id == expected_user_id)
    
    if result:
        print(f"Success! Extracted status_key: {status_key}, user_id: {user_id}")
    else:
        print(f"Failure! Expected status_key: {expected_status_key}, user_id: {expected_user_id}")
        print(f"Got status_key: {status_key}, user_id: {user_id}")
    
    return result

# Test cases
test_cases = [
    ("my_status_new_123456", "new", "123456"),
    ("my_status_in_progress_123456", "in_progress", "123456"),
    ("my_status_completed_123456", "completed", "123456"),
    ("my_status_rejected_123456", "rejected", "123456")
]

# Run tests
all_passed = True
for callback_data, expected_status_key, expected_user_id in test_cases:
    if not test_callback_parsing(callback_data, expected_status_key, expected_user_id):
        all_passed = False
    print("-" * 50)

if all_passed:
    print("All tests passed!")
else:
    print("Some tests failed!")