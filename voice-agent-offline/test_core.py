import os
from main import get_intent, split_commands, is_destructive
from nerve_center import ProjectIndexer

def test_get_intent_fast_paths():
    # Test sleep boundaries
    res = get_intent("put the pc to sleep")
    assert res["intent"] == "system"
    
    # Test play/media vs vision
    res_vision = get_intent("what's on my display")
    assert res_vision["intent"] == "vision"
    
    res_media = get_intent("play the next song")
    assert res_media["intent"] == "media"
    
    res_type = get_intent("type hello world")
    assert res_type["intent"] == "type"

def test_split_commands():
    # Test splitting by "and" / "then"
    commands = split_commands("open chrome and then play music")
    assert len(commands) == 2
    
    commands2 = split_commands("go to google and search for cats")
    # if "search for cats" doesn't map to a specific intent, it joins them
    # But let's check it doesn't crash
    assert len(commands2) >= 1



def test_nerve_center():
    indexer = ProjectIndexer(".")
    indexer.index["test_func"] = [{"file": "test.py", "line": 1, "type": "function", "absolute_path": "/test.py"}]
    
    res = indexer.find_target("test_func")
    assert len(res) == 1
    assert res[0]["file"] == "test.py"
