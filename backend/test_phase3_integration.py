"""Phase 3 集成测试:视频历史库 + RAG 端到端验证。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import init_db, reset_engine
from app.models.state import VideoGenerationState, TaskStatus
from app.schemas.requirement import StructuredRequirement, Character, Scene
from app.schemas.script import VideoScript, ScriptScene
from app.schemas.storyboard import Storyboard, StoryboardShot
from app.providers.llm.mock_llm import MockLLMProvider
from app.knowledge.embedding_provider import EmbeddingProvider
from app.knowledge.metadata_extractor import extract_metadata
from app.knowledge.semantic_extractor import SemanticExtractor
from app.knowledge.video_indexer import VideoIndexer
from app.knowledge.video_searcher import VideoSearcher
from app.knowledge.vector_store import vector_store


async def test_rag_flow():
    llm = MockLLMProvider()

    # 1. Test embedding provider (Mock mode)
    ep = EmbeddingProvider()
    assert ep._mock or ep._client is not None, "Embedding provider should initialize"
    vec = await ep.embed("测试文本")
    assert len(vec) > 0, f"Embedding should return non-empty vector, got len={len(vec)}"
    vec2 = await ep.embed("测试文本")
    assert vec == vec2, "Same text should produce same embedding (deterministic)"
    print(f"1. EmbeddingProvider: Mock mode OK, dim={len(vec)}")

    # 2. Build a fake completed video state
    state = VideoGenerationState(
        task_id="test_rag_001",
        user_id="rag_test_user",
        user_input="假如古代人有手机",
        duration=10,
        style="古装喜剧",
        aspect_ratio="9:16",
        status=TaskStatus.COMPLETED,
        video_path="/storage/videos/test_rag_001.mp4",
        requirement=StructuredRequirement(
            topic="古代人第一次刷短视频",
            genre="轻喜剧",
            duration=10,
            style="古装喜剧",
            characters=[Character(name="主角", description="古代书生")],
            scenes=[Scene(location="书房", description="古代书房场景")],
        ),
        script=VideoScript(
            title="古人刷短视频",
            hook="一个古代书生第一次看到短视频",
            scenes=[
                ScriptScene(scene_id=1, duration=5, location="书房", characters=["主角"],
                            visual="书生看到手机屏幕", voiceover="古代书生第一次刷短视频"),
                ScriptScene(scene_id=2, duration=5, location="书房", characters=["主角"],
                            visual="书生笑出声", voiceover="他被短视频逗笑了"),
            ],
        ),
        storyboard=Storyboard(shots=[
            StoryboardShot(scene_id=1, duration=5, visual_description="书生看到手机", image_prompt="ancient scholar phone"),
            StoryboardShot(scene_id=2, duration=5, visual_description="书生大笑", image_prompt="ancient scholar laughing"),
        ]),
        quality_report={"grade": "A", "duration": 10.0, "has_audio": True},
    )

    # 3. Test metadata extraction
    metadata = extract_metadata(state)
    assert metadata["title"] == "古人刷短视频", f"Title mismatch: {metadata['title']}"
    assert metadata["topic"] == "古代人第一次刷短视频"
    assert metadata["quality_grade"] == "A"
    assert "古装喜剧" in metadata["tags"]
    assert metadata["shot_count"] == 2
    print(f"2. MetadataExtractor: title={metadata['title']}, grade={metadata['quality_grade']}, tags={metadata['tags']}")

    # 4. Test semantic extraction
    se = SemanticExtractor(llm=llm)
    desc = await se.extract(state)
    assert len(desc) > 0, "Semantic description should be non-empty"
    print(f"3. SemanticExtractor: len={len(desc)}, preview={desc[:60]}...")

    # 5. Test video indexer (full flow: metadata → semantic → embedding → Milvus)
    indexer = VideoIndexer(llm=llm)
    await indexer.index(state)
    print("4. VideoIndexer: index completed")

    # 6. Test video searcher
    searcher = VideoSearcher()
    results = await searcher.search("古代人搞笑", user_id="rag_test_user", top_k=5)
    assert len(results) > 0, f"Search should return results, got {len(results)}"
    assert results[0]["video_id"] == "test_rag_001", f"Expected video_id=test_rag_001, got {results[0]['video_id']}"
    print(f"5. VideoSearcher: found {len(results)} results, top score={results[0]['score']:.4f}")

    # 7. Test user isolation (different user should get no results)
    results_other = await searcher.search("古代人搞笑", user_id="other_user", top_k=5)
    assert len(results_other) == 0, f"Other user should get 0 results, got {len(results_other)}"
    print(f"6. User isolation: other user got {len(results_other)} results (expected 0)")

    # 8. Cleanup
    vector_store.delete_by_video("test_rag_001")
    print("7. Cleanup: vector deleted")

    print("\n=== Phase 3 integration tests ALL PASSED ===")


async def main():
    reset_engine()
    await init_db()
    await test_rag_flow()
    reset_engine()


asyncio.run(main())
