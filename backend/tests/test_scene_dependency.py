"""针对性验证:Scene 级依赖传播(改 Scene 3 仅重生成其关联镜头链)。"""
import sys
sys.path.insert(0, r"d:\VideoForge\backend")

from app.models.state import VideoGenerationState
from app.schemas.script import VideoScript, ScriptScene
from app.schemas.storyboard import Storyboard, StoryboardShot
from app.orchestrator.orchestrator import Orchestrator

state = VideoGenerationState(task_id="test-scene-dep", user_input="测试创意")
state.script = VideoScript(
    title="t", hook="",
    scenes=[
        ScriptScene(scene_id=i + 1, duration=5, location="L", characters=[], visual="v", dialogue="", voiceover="")
        for i in range(4)
    ],
)
state.storyboard = Storyboard(shots=[
    StoryboardShot(scene_id=1, shot_id="s1", duration=5, shot_type="medium shot", camera_movement="static",
                   visual_description="v", character_action="", dialogue="", voiceover="",
                   image_prompt="p", video_prompt="p", negative_prompt=""),
    StoryboardShot(scene_id=2, shot_id="s2", duration=5, shot_type="medium shot", camera_movement="static",
                   visual_description="v", character_action="", dialogue="", voiceover="",
                   image_prompt="p", video_prompt="p", negative_prompt=""),
    StoryboardShot(scene_id=3, shot_id="s3", duration=5, shot_type="medium shot", camera_movement="static",
                   visual_description="v", character_action="", dialogue="", voiceover="",
                   image_prompt="p", video_prompt="p", negative_prompt=""),
    StoryboardShot(scene_id=3, shot_id="s3b", duration=5, shot_type="close-up", camera_movement="static",
                   visual_description="v", character_action="", dialogue="", voiceover="",
                   image_prompt="p", video_prompt="p", negative_prompt=""),
    StoryboardShot(scene_id=4, shot_id="s4", duration=5, shot_type="medium shot", camera_movement="static",
                   visual_description="v", character_action="", dialogue="", voiceover="",
                   image_prompt="p", video_prompt="p", negative_prompt=""),
])

# 修改 Scene 3(索引 2)
impact = Orchestrator.analyze_scene_dependencies(state, 2)
affected = [i + 1 for i in impact["affected"]]
unaffected = [i + 1 for i in impact["unaffected"]]
print("修改 Scene 3 -> affected shots:", affected)
print("修改 Scene 3 -> unaffected shots:", unaffected)
assert affected == [3, 4], f"预期 [3,4], 实际 {affected}"
assert unaffected == [1, 2, 5], f"预期 [1,2,5], 实际 {unaffected}"

# 锁定镜头 3 后再改 Scene 3
state.storyboard.shots[2].locked = True
impact2 = Orchestrator.analyze_scene_dependencies(state, 2)
affected2 = [i + 1 for i in impact2["affected"]]
locked2 = [i + 1 for i in impact2["locked"]]
print("锁定镜头3后修改 Scene 3 -> affected:", affected2, "locked:", locked2)
assert affected2 == [4] and locked2 == [3]

# 路由注册检查
from app.api.routes import router
paths = {r.path for r in router.routes}
assert "/api/video/tasks/{task_id}/scenes/{scene_index}/impact" in paths, paths
assert "/api/video/tasks/{task_id}/scenes/{scene_index}/revise" in paths, paths
print("routes OK:", [p for p in paths if "scenes" in p])
print("ALL PASS")
