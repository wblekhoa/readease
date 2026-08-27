import errno
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import huggingface_hub

from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.speech.vieneu import (
    CODEC_DIRECTORY,
    CODEC_FILES,
    CODEC_REPO,
    CODEC_REVISION,
    MODEL_DIRECTORY,
    MODEL_FILES,
    MODEL_REPO,
    MODEL_REVISION,
    MODEL_SUBFOLDER,
    ModelPreparationError,
    VieNeuSpeechEngine,
    _load_sdk,
    _local_codec_downloads,
)


class FakeAudioArray:
    dtype = "float32"
    ndim = 1

    def __init__(self, *samples: float):
        self._pcm = struct.pack(f"<{len(samples)}f", *samples)

    def astype(self, dtype, copy=False):
        if dtype not in ("float32", "<f4"):
            raise AssertionError(f"unexpected dtype: {dtype}")
        return self

    def tobytes(self):
        return self._pcm


class FakeVieNeuSDK:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.stream_calls = []

    def list_preset_voices(self):
        return [("Adam — Nam Bộ", "Adam"), ("Trúc Ly — Bắc Bộ", "Trúc Ly")]

    def infer_stream(self, text, **kwargs):
        self.stream_calls.append((text, kwargs))
        yield FakeAudioArray(0.1, -0.1)
        yield FakeAudioArray(0.2, -0.2)


class VieNeuSpeechEngineContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models = Path(self.temp_dir.name) / "Models"
        self.created = []
        self.original_offline = os.environ.pop("HF_HUB_OFFLINE", None)

        def factory(**kwargs):
            self.assertEqual(os.environ["HF_HOME"], str(self.models))
            self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "1")
            self.assertEqual(os.environ["DO_NOT_TRACK"], "1")
            sdk = FakeVieNeuSDK(**kwargs)
            self.created.append(sdk)
            return sdk

        self.engine = VieNeuSpeechEngine(self.models, sdk_factory=factory)

    def tearDown(self):
        if self.original_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = self.original_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)
        self.temp_dir.cleanup()

    def test_sdk_is_lazy_singleton_with_onnx_int8_configuration(self):
        self.assertEqual(self.created, [])

        voices = self.engine.voices()
        list(self.engine.stream("Xin chào", "Adam"))

        self.assertEqual(len(self.created), 1)
        self.assertEqual(
            self.created[0].kwargs,
            {"mode": "v3turbo", "backend": "onnx", "precision": "int8"},
        )
        self.assertEqual([(voice.id, voice.label) for voice in voices], [
            ("Adam", "Adam — Nam Bộ"),
            ("Trúc Ly", "Trúc Ly — Bắc Bộ"),
        ])

    def test_stream_converts_each_sdk_array_to_48khz_float32_audio(self):
        chunks = tuple(
            self.engine.stream(
                "Xin chào",
                "Adam",
                SynthesisSettings(temperature=0.7),
            )
        )

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(chunk.sample_rate == 48_000 for chunk in chunks))
        self.assertEqual(chunks[0].pcm, struct.pack("<2f", 0.1, -0.1))
        text, settings = self.created[0].stream_calls[0]
        self.assertEqual(text, "Xin chào")
        self.assertEqual(settings["voice"], "Adam")
        self.assertEqual(settings["temperature"], 0.7)

    def test_long_text_is_forwarded_with_the_sdk_chunking_limit(self):
        source = " ".join(["Đây là một câu tiếng Việt rõ ràng."] * 20)

        tuple(self.engine.stream(source, "Adam"))

        text, settings = self.created[0].stream_calls[0]
        self.assertGreater(len(text), 240)
        self.assertEqual(text, source)
        self.assertEqual(settings["max_chars"], 240)

    def test_cancel_stops_an_existing_iterator_before_the_next_chunk(self):
        iterator = self.engine.stream("Xin chào", "Adam")
        first = next(iterator)

        self.engine.cancel()

        self.assertTrue(first.pcm)
        self.assertEqual(list(iterator), [])

    def test_empty_text_is_rejected_before_sdk_initialization(self):
        with self.assertRaisesRegex(ValueError, "text"):
            list(self.engine.stream(" \n", "Adam"))

        self.assertEqual(self.created, [])

    def test_model_and_codec_revisions_are_full_pinned_commits(self):
        self.assertEqual(
            MODEL_REVISION,
            "2da0efab622a1722125991736524f080b751ef5b",
        )
        self.assertEqual(
            CODEC_REVISION,
            "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
        )

    def test_prepare_model_downloads_the_pinned_snapshot_and_marks_full_readiness(self):
        download_calls = []

        def download_model(**kwargs):
            download_calls.append(kwargs)
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            elif kwargs["repo_id"] == CODEC_REPO:
                filenames = CODEC_FILES
            else:
                raise AssertionError(f"unexpected repo: {kwargs['repo_id']}")
            target.mkdir(parents=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(kwargs["local_dir"])

        created = []

        def prepared_factory(**kwargs):
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            sdk = FakeVieNeuSDK(**kwargs)
            created.append(sdk)
            return sdk

        progress = Mock()
        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=prepared_factory,
            model_downloader=download_model,
        )

        self.assertFalse(engine.is_model_ready)
        engine.prepare_model(progress)

        self.assertTrue(engine.is_model_ready)
        self.assertEqual(len(download_calls), 2)
        self.assertEqual(download_calls[0]["revision"], MODEL_REVISION)
        self.assertEqual(download_calls[0]["repo_id"], MODEL_REPO)
        self.assertEqual(download_calls[1]["revision"], CODEC_REVISION)
        self.assertEqual(download_calls[1]["repo_id"], CODEC_REPO)
        self.assertEqual(download_calls[1]["allow_patterns"], list(CODEC_FILES))
        self.assertEqual(
            created[0].kwargs,
            {
                "mode": "v3turbo",
                "backend": "onnx",
                "precision": "int8",
                "backbone_repo": str(self.models / MODEL_DIRECTORY),
                "onnx_dir": str(
                    self.models / MODEL_DIRECTORY / MODEL_SUBFOLDER
                ),
                "codec_dir": str(self.models / CODEC_DIRECTORY),
            },
        )
        progress.assert_any_call(1.0, "Mô hình đọc tiếng Việt đã sẵn sàng.")

        restarted_created = []
        def restarted_factory(**kwargs):
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            sdk = FakeVieNeuSDK(**kwargs)
            restarted_created.append(sdk)
            return sdk

        restarted = VieNeuSpeechEngine(
            self.models,
            sdk_factory=restarted_factory,
            model_downloader=download_model,
        )
        restarted.voices()
        self.assertEqual(restarted_created[0].kwargs, created[0].kwargs)
        self.assertEqual(len(download_calls), 2)

    def test_missing_codec_asset_invalidates_an_existing_ready_marker(self):
        def download_model(**kwargs):
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            else:
                filenames = CODEC_FILES
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(target)

        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **kwargs: FakeVieNeuSDK(**kwargs),
            model_downloader=download_model,
        )
        engine.prepare_model(Mock())
        self.assertTrue(engine.is_model_ready)

        (self.models / CODEC_DIRECTORY / CODEC_FILES[0]).unlink()

        self.assertFalse(engine.is_model_ready)

    def test_preparation_leaves_no_duplicate_hub_cache_under_the_models_root(self):
        residue = (
            self.models
            / "hub"
            / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX"
            / "snapshots"
            / CODEC_REVISION
        )

        def download_model(**kwargs):
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            else:
                filenames = CODEC_FILES
                residue.mkdir(parents=True, exist_ok=True)
                for filename in filenames:
                    (residue / filename).write_bytes(b"fixture")
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(target)

        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **kwargs: FakeVieNeuSDK(**kwargs),
            model_downloader=download_model,
        )

        engine.prepare_model(Mock())

        self.assertTrue(engine.is_model_ready)
        self.assertFalse((self.models / "hub").exists())
        self.assertTrue(
            (self.models / CODEC_DIRECTORY / CODEC_FILES[0]).is_file()
        )

    def test_preparation_clears_hub_residue_left_by_an_earlier_install(self):
        download_calls = []

        def download_model(**kwargs):
            download_calls.append(kwargs)
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            else:
                filenames = CODEC_FILES
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(target)

        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **kwargs: FakeVieNeuSDK(**kwargs),
            model_downloader=download_model,
        )
        engine.prepare_model(Mock())
        residue = (
            self.models
            / "hub"
            / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX"
        )
        residue.mkdir(parents=True)
        (residue / CODEC_FILES[0]).write_bytes(b"fixture")

        engine.prepare_model(Mock())

        self.assertEqual(len(download_calls), 2)
        self.assertTrue(engine.is_model_ready)
        self.assertFalse((self.models / "hub").exists())

    def test_preparation_keeps_hub_entries_outside_the_two_pinned_repositories(self):
        def download_model(**kwargs):
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            else:
                filenames = CODEC_FILES
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(target)

        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **kwargs: FakeVieNeuSDK(**kwargs),
            model_downloader=download_model,
        )
        engine.prepare_model(Mock())
        hub = self.models / "hub"
        pinned = (
            hub / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo",
            hub / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX",
            hub / ".locks" / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX",
        )
        unrelated = hub / "models--some-other--repo"
        for directory in pinned + (unrelated,):
            directory.mkdir(parents=True)
            (directory / "blob").write_bytes(b"fixture")
        tag = hub / "CACHEDIR.TAG"
        tag.write_bytes(b"Signature: 8a477f597d28d172789f06886806bc55")

        engine.prepare_model(Mock())

        for directory in pinned:
            self.assertFalse(directory.exists())
        self.assertTrue((unrelated / "blob").is_file())
        self.assertTrue(tag.is_file())

    def test_hub_cleanup_never_deletes_through_a_symlinked_component(self):
        def download_model(**kwargs):
            target = Path(kwargs["local_dir"])
            if kwargs["repo_id"] == MODEL_REPO:
                target = target / MODEL_SUBFOLDER
                filenames = MODEL_FILES
            else:
                filenames = CODEC_FILES
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (target / filename).write_bytes(b"fixture")
            return str(target)

        pinned = "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX"
        for component in ("hub", "repository", "locks"):
            with self.subTest(component=component):
                models = Path(self.temp_dir.name) / f"models-{component}"
                outside = Path(self.temp_dir.name) / f"outside-{component}"
                (outside / pinned).mkdir(parents=True)
                (outside / pinned / "keep.bin").write_bytes(b"fixture")
                engine = VieNeuSpeechEngine(
                    models,
                    sdk_factory=lambda **kwargs: FakeVieNeuSDK(**kwargs),
                    model_downloader=download_model,
                )
                engine.prepare_model(Mock())
                hub = models / "hub"
                if component == "hub":
                    hub.symlink_to(outside, target_is_directory=True)
                elif component == "repository":
                    hub.mkdir()
                    (hub / pinned).symlink_to(
                        outside / pinned,
                        target_is_directory=True,
                    )
                else:
                    hub.mkdir()
                    (hub / ".locks").symlink_to(outside, target_is_directory=True)

                engine.prepare_model(Mock())

                self.assertTrue(engine.is_model_ready)
                self.assertTrue((outside / pinned / "keep.bin").is_file())

    def test_codec_download_override_is_scoped_local_and_fail_closed(self):
        codec_directory = self.models / CODEC_DIRECTORY
        codec_directory.mkdir(parents=True)
        local_asset = codec_directory / CODEC_FILES[0]
        local_asset.write_bytes(b"fixture")
        original = Mock(return_value="upstream-result")

        with patch.object(huggingface_hub, "hf_hub_download", original):
            with _local_codec_downloads(codec_directory):
                self.assertEqual(
                    huggingface_hub.hf_hub_download(CODEC_REPO, CODEC_FILES[0]),
                    str(local_asset),
                )
                with self.assertRaises(FileNotFoundError):
                    huggingface_hub.hf_hub_download("another/repo", "asset.bin")
                with self.assertRaises(FileNotFoundError):
                    huggingface_hub.hf_hub_download(CODEC_REPO, "../escape")
                with self.assertRaises(FileNotFoundError):
                    huggingface_hub.hf_hub_download(CODEC_REPO, CODEC_FILES[1])
            self.assertIs(huggingface_hub.hf_hub_download, original)

    def test_default_sdk_adapter_consumes_local_codec_without_forwarding_it(self):
        codec_directory = self.models / CODEC_DIRECTORY
        codec_directory.mkdir(parents=True)
        local_asset = codec_directory / CODEC_FILES[0]
        local_asset.write_bytes(b"fixture")

        def fake_vieneu(**kwargs):
            resolved = huggingface_hub.hf_hub_download(
                CODEC_REPO,
                CODEC_FILES[0],
            )
            return kwargs, resolved

        with patch("vieneu.Vieneu", side_effect=fake_vieneu):
            arguments, resolved = _load_sdk(
                codec_dir=str(codec_directory),
                mode="v3turbo",
                backend="onnx",
            )

        self.assertEqual(arguments, {"mode": "v3turbo", "backend": "onnx"})
        self.assertEqual(resolved, str(local_asset))

    def test_failed_model_preparation_never_publishes_a_ready_marker(self):
        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **_kwargs: FakeVieNeuSDK(),
            model_downloader=Mock(side_effect=OSError("network unavailable")),
        )

        with self.assertRaisesRegex(RuntimeError, "chuẩn bị"):
            engine.prepare_model(Mock())

        self.assertFalse(engine.is_model_ready)

    def test_a_full_disk_is_not_reported_as_a_network_problem(self):
        def direct(**_kwargs):
            raise OSError(errno.ENOSPC, "No space left on device")

        def wrapped(**_kwargs):
            try:
                raise OSError(errno.ENOSPC, "No space left on device")
            except OSError as error:
                raise RuntimeError("download failed") from error

        for downloader in (direct, wrapped):
            with self.subTest(downloader=downloader.__name__):
                engine = VieNeuSpeechEngine(
                    self.models,
                    sdk_factory=lambda **_kwargs: FakeVieNeuSDK(),
                    model_downloader=downloader,
                )

                with self.assertRaises(ModelPreparationError) as failure:
                    engine.prepare_model(Mock())

                self.assertIn("dung lượng", str(failure.exception))
                self.assertNotIn("mạng", str(failure.exception))
                self.assertFalse(engine.is_model_ready)

    def test_a_failure_that_is_not_about_space_still_names_the_network(self):
        engine = VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **_kwargs: FakeVieNeuSDK(),
            model_downloader=Mock(side_effect=OSError("connection reset")),
        )

        with self.assertRaises(ModelPreparationError) as failure:
            engine.prepare_model(Mock())

        self.assertIn("mạng", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
