# Demo checklist

Run through this 30 minutes before judging, and again 5 minutes before.

## 1. Start the backend (terminal 1)

```bash
cd highground
```

```bash
source .venv/bin/activate
```

```bash
pytest
```

```bash
uvicorn highground.main:app --env-file .env
```

No `--reload` on demo day, so a stray file save can't restart the server mid-pitch.

## 2. Start the web app (terminal 2)

```bash
cd highground/web
```

```bash
npm run dev
```

## 3. Check the API

```bash
curl -s "http://localhost:8000/api/assess?mode=replay"
```

You should see red paddocks and a recommendation naming a paddock. Note which one: the presenter reads it off the banner as [paddock shown].

## 4. Browser tabs (in this order)

1. `http://localhost:5173` — the app, on the sample farm, in calm mode (all green). Zoom so the whole farm fits.
2. The backup video, open and paused at 0:00 (see section 6).
3. `http://localhost:8000/docs` — only if a judge asks to see the API.
4. `docs/pitch.md` on GitHub — for the speaker, on a second screen or phone, not the projector.

Close everything else. Turn off notifications (Do Not Disturb). Set browser zoom so the banner text is readable from the back of the room.

## 5. Wi-Fi off fallback

Replay mode and the template plan work without internet:

- Replay uses the saved warning in `data/replay_warning.xml`.
- With no Gemini access, the plan falls back to the built-in template (the plan screen shows "Written by: template").
- Map tiles from OpenStreetMap need internet. Without it the paddocks still draw and colour, on a blank background.

Test it once before the event: turn Wi-Fi off, reload the app, press **Replay warning**, then **Show plan**. If it works, you're safe.

If the venue Wi-Fi is slow, turn it off before the pitch rather than risk a half-loaded map. [TBD: decide whether to pre-load map tiles by panning the farm once while online.]

## 6. Backup video

- [ ] Record the full demo path (load farm → Replay warning → red paddocks and banner → Show plan → Copy as text), about 60–90 s, no audio needed.
- [ ] Save it locally on the demo laptop and on a USB stick: [TBD file name / location].
- [ ] If the live app fails twice, stop fixing it, say "Here's the recording", and play the video. Keep talking over it from the script.

## 7. Who clicks what

| Moment | Speaker | Clicker |
|---|---|---|
| Hook, problem | [TBD name] | hands off the laptop |
| Replay warning | [TBD name] | [TBD name] clicks **Replay warning** |
| Point at paddocks and banner | [TBD name] | holds the mouse still |
| Show plan | [TBD name] | clicks **Show plan** |
| Copy as text | [TBD name] | clicks **Copy as text**, waits for "Copied" |
| How it works, farmer, close | [TBD name] | clicks **Reset** after the close, ready for questions |
| Judge questions | everyone | [TBD name] drives the app if asked |

## 8. Last checks

- [ ] Set the demo laptop to NZ time
- [ ] Open the app once while online so map tiles are cached
- [ ] `pytest` passes
- [ ] Banner shows **REPLAY** in replay mode
- [ ] Safety line visible: "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee."
- [ ] About screen shows the data credits
- [ ] Laptop charged and plugged in; HDMI/USB-C adapter tested with the venue projector
- [ ] Code frozen 1 hour before judging (only demo-breaking fixes)
