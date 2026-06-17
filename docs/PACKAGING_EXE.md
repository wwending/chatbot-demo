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

The desktop client uses demo weather when no API key is configured. To enable real weather:

1. Create a `.env` file next to `chatbot-demo.exe`.
2. Add your OpenWeather API key:

```env
WEATHER_API_KEY=your_openweather_api_key
```

3. Restart the desktop client.

The built-in weather tool calls:

```text
https://api.openweathermap.org/data/2.5/weather
```

## Notes

- The GUI is implemented with Tkinter, so no extra desktop UI dependency is required.
- The app calls the existing Python chat service directly instead of going through HTTP.
- The default knowledge files are bundled into the exe and copied to the runtime `knowledge\` folder on first launch.
