# Developer Notes

```bash
# Create the project directory
uv init cache_me_if_you_can
cd cache_me_if_you_can

# Install Python 3.14 specifically for this project
# uv will download a standalone build if you don't have it
uv python install 3.14

uv add streamlit
uv add "valkey[libvalkey]"
uv add pandas
uv add plotly
```
