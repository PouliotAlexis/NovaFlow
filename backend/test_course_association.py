import os
import sys
import uuid

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
from app.services.task_manager import TaskManager

def test_course_association():
    print("🚀 Testing Task-Course Association...")
    tm = TaskManager.instance()
    
    test_title = f"Test Task {uuid.uuid4().hex[:6]}"
    test_course_id = "IFT-1000"
    
    print(f"➕ Adding task: '{test_title}' for course '{test_course_id}'")
    task = tm.add_task(
        title=test_title,
        course_id=test_course_id,
        meta="Test Script"
    )
    
    print(f"✅ Task created with ID: {task['id']}")
    print(f"📊 course_id in returned task: {task.get('course_id')}")
    
    if task.get('course_id') == test_course_id:
        print("✨ SUCCESS: course_id is correctly set in returned object.")
    else:
        print(f"❌ FAILURE: course_id is {task.get('course_id')}, expected {test_course_id}")
        return False

    # Reload and check
    print("🔄 Reloading TaskManager from disk...")
    tm.reload()
    found_task = tm.get_task_object(task['id'])
    
    if found_task and found_task.course_id == test_course_id:
        print("✨ SUCCESS: course_id is correctly persisted to disk.")
    else:
        print(f"❌ FAILURE: course_id not found or incorrect after reload.")
        return False
        
    # Cleanup
    print(f"🧹 Deleting test task {task['id']}")
    tm.delete_task(task['id'])
    
    print("\n🎉 ALL TESTS PASSED!")
    return True

if __name__ == "__main__":
    if test_course_association():
        sys.exit(0)
    else:
        sys.exit(1)
