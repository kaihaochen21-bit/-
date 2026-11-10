from app.media import _format_srt_time, write_srt


def test_srt_format(tmp_path):
    path = tmp_path / "a.srt"
    write_srt([{"duration": 2.5, "narration": "第一句"}, {"duration": 3, "narration": "第二句"}], path)
    text = path.read_text(encoding="utf-8")
    assert "00:00:02,500 --> 00:00:05,500" in text
    assert "第二句" in text
    assert _format_srt_time(65.25) == "00:01:05,250"
