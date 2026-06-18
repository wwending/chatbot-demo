# Windows Desktop EXE Packaging

This branch packages the chatbot as a native Windows desktop client. It does not start a browser and does not require the React dev server.

## Build

From the project root:

```powershell
.\packaging\build_exe.ps1
```

If dependencies are already installed:

```powershell
.\packaging\build_exe.ps1 -SkipInstall
```

The output is:

```text
dist\chatbot-demo.exe
```

Only `dist` is used for formal builds.

The build script enables a UTF-8 Python environment before packaging so Chinese UI text is preserved.

## Run

Double-click the exe or run:

```powershell
.\dist\chatbot-demo.exe
```

The desktop window includes:

- Session list and user ID selection
- Chat message area
- System status
- Tool result and RAG source details
- Default knowledge import
- Local `.txt` / `.md` knowledge upload

Runtime data is written next to the exe:

```text
data\chatbot.db
data\vector_store.json
knowledge\
```

## Weather API

The desktop client uses Open-Meteo for weather lookup and does not require an API key. Users can ask for current weather and forecasts, such as `上海天气怎么样`, `明天临沂天气`, `武汉未来一周天气`, `未来十五天武汉天气`, or `New York weather`.

The built-in weather tool calls:

```text
https://geocoding-api.open-meteo.com/v1/search
https://api.open-meteo.com/v1/forecast
```

The Forecast API is used for both current weather and daily forecast. Future weather supports tomorrow, the day after tomorrow, and future N-day ranges up to 16 days. Queries beyond 16 days return a friendly limit message instead of calling Open-Meteo for the unsupported range.

The `.env` file is still used for model settings such as `LLM_API_KEY`, but packaged builds do not need `WEATHER_API_KEY` in `dist\.env`.

## Notes

- The GUI is implemented with Tkinter, so no extra desktop UI dependency is required.
- The app calls the existing Python chat service directly instead of going through HTTP.
- The default knowledge files are bundled into the exe and copied to the runtime `knowledge\` folder on first launch.
