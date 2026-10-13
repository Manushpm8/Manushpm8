from profile_card.config import Config, load_config


def test_load_config_reads_every_field(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'handle = "manush"\nusername = "Manushpm8"\nhost = "github"\nos = "macOS"\n'
        'role = "AI Engineer @ NVIDIA"\nlocation = "Sunnyvale, CA"\n'
        'focus = "Structured & graph foundation models"\nlanguages = ["Python", "SQL"]\n'
        'github_url = "https://github.com/Manushpm8"\n'
        'linkedin_url = "https://www.linkedin.com/in/manushmurali"\n'
    )
    config = load_config(path)
    assert config == Config(
        handle="manush",
        username="Manushpm8",
        host="github",
        os="macOS",
        role="AI Engineer @ NVIDIA",
        location="Sunnyvale, CA",
        focus="Structured & graph foundation models",
        languages=("Python", "SQL"),
        github_url="https://github.com/Manushpm8",
        linkedin_url="https://www.linkedin.com/in/manushmurali",
    )
