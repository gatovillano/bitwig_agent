package com.bitwig.agent;

import com.bitwig.extension.controller.api.*;
import com.bitwig.extension.api.Color;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/**
 * Embedded HTTP server providing a RESTful JSON API to control Bitwig Studio.
 * All mutations on the Bitwig model are safely scheduled onto the controller thread via host.scheduleTask().
 */
public class BridgeHttpServer {

    private final BitwigAgentExtension extension;
    private final ControllerHost host;
    private final int port;
    private HttpServer server;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public BridgeHttpServer(BitwigAgentExtension extension, ControllerHost host, int port) {
        this.extension = extension;
        this.host = host;
        this.port = port;
    }

    public void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.setExecutor(executor);

        server.createContext("/api/status", new StatusHandler());
        server.createContext("/api/project", new ProjectHandler());
        server.createContext("/api/transport", new TransportHandler());
        server.createContext("/api/track/select", new TrackSelectHandler());
        server.createContext("/api/clip/create", new ClipCreateHandler());
        server.createContext("/api/clip/notes", new ClipNotesHandler());
        server.createContext("/api/clip/clear", new ClipClearHandler());
        server.createContext("/api/clip/launch", new ClipLaunchHandler());
        server.createContext("/api/scene/launch", new SceneLaunchHandler());
        server.createContext("/api/instrument/add", new InstrumentAddHandler());
        server.createContext("/api/effect/add", new EffectAddHandler());
        server.createContext("/api/device/control", new DeviceControlHandler());
        server.createContext("/api/device/parameter", new DeviceParameterHandler());
        server.createContext("/api/track/inspect", new TrackInspectHandler());
        server.createContext("/api/clip/inspect", new ClipInspectHandler());
        server.createContext("/api/arranger/inspect", new ArrangerInspectHandler());
        server.createContext("/api/track/move", new TrackMoveHandler());
        server.createContext("/api/track/group", new TrackGroupHandler());
        server.createContext("/api/track/ungroup", new TrackUngroupHandler());
        server.createContext("/api/track/rename", new TrackRenameHandler());
        server.createContext("/api/track/control", new TrackControlHandler());
        server.createContext("/api/actions", new ActionsHandler());

        server.start();
        host.println("[BitwigAgent] REST server listening on http://127.0.0.1:" + port);
    }

    public void stop() {
        if (server != null) {
            server.stop(0);
        }
        executor.shutdownNow();
    }

    // Helper to run code safely on Bitwig's main controller thread
    public <T> CompletableFuture<T> runOnBitwigThread(Callable<T> callable) {
        CompletableFuture<T> future = new CompletableFuture<>();
        host.scheduleTask(() -> {
            try {
                T result = callable.call();
                future.complete(result);
            } catch (Throwable t) {
                future.completeExceptionally(t);
            }
        }, 0);
        return future;
    }

    private static void handleCors(HttpExchange exchange) {
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type, Authorization");
    }

    private static void sendJson(HttpExchange exchange, int statusCode, Object data) throws IOException {
        handleCors(exchange);
        byte[] bytes = JsonUtils.toJson(data).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(statusCode, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static String readBody(HttpExchange exchange) throws IOException {
        try (InputStream is = exchange.getRequestBody();
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buf = new byte[1024];
            int r;
            while ((r = is.read(buf)) != -1) {
                baos.write(buf, 0, r);
            }
            return baos.toString(StandardCharsets.UTF_8);
        }
    }

    // --- HANDLERS ---

    private class StatusHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("status", "ok");
            resp.put("name", "Bitwig Agent Bridge");
            resp.put("version", "1.0.0");
            resp.put("bitwig_api", extension.getApiVersion());
            sendJson(exchange, 200, resp);
        }
    }

    private class ProjectHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                Map<String, Object> state = runOnBitwigThread(() -> {
                    Map<String, Object> data = new LinkedHashMap<>();
                    Transport transport = extension.getTransport();
                    data.put("tempo", transport.tempo().value().getRaw());
                    data.put("isPlaying", transport.isPlaying().get());
                    data.put("isRecording", transport.isArrangerRecordEnabled().get());
                    data.put("position", transport.getPosition().get());

                    List<Map<String, Object>> tracksList = new ArrayList<>();
                    TrackBank bank = extension.getTrackBank();
                    int size = bank.getSizeOfBank();
                    for (int i = 0; i < size; i++) {
                        Track t = (Track) bank.getItemAt(i);
                        if (!t.exists().get()) continue;

                        Map<String, Object> tInfo = new LinkedHashMap<>();
                        tInfo.put("index", i);
                        tInfo.put("name", t.name().get());
                        tInfo.put("type", t.trackType().get());
                        tInfo.put("volume", t.volume().displayedValue().get());
                        tInfo.put("pan", t.pan().displayedValue().get());
                        tInfo.put("isGroup", t.isGroup().get());
                        tInfo.put("arm", t.arm().get());
                        tInfo.put("mute", t.mute().get());
                        tInfo.put("solo", t.solo().get());

                        List<Map<String, Object>> devices = new ArrayList<>();
                        DeviceBank devBank = extension.getDeviceBank(i);
                        if (devBank != null) {
                            for (int d = 0; d < 16; d++) {
                                Device dev = devBank.getDevice(d);
                                if (!dev.exists().get()) continue;
                                Map<String, Object> dInfo = new LinkedHashMap<>();
                                dInfo.put("index", d);
                                dInfo.put("name", dev.name().get());
                                dInfo.put("type", dev.deviceType().get());
                                dInfo.put("preset", dev.presetName().get());
                                dInfo.put("isEnabled", dev.isEnabled().get());
                                dInfo.put("isPlugin", dev.isPlugin().get());
                                devices.add(dInfo);
                            }
                        }
                        tInfo.put("devices", devices);

                        List<Map<String, Object>> slots = new ArrayList<>();
                        ClipLauncherSlotBank slotBank = t.clipLauncherSlotBank();
                        for (int s = 0; s < 16; s++) {
                            ClipLauncherSlot slot = (ClipLauncherSlot) slotBank.getItemAt(s);
                            Map<String, Object> sInfo = new LinkedHashMap<>();
                            sInfo.put("index", s);
                            sInfo.put("hasContent", slot.hasContent().get());
                            sInfo.put("isPlaying", slot.isPlaying().get());
                            sInfo.put("isSelected", slot.isSelected().get());
                            slots.add(sInfo);
                        }
                        tInfo.put("slots", slots);
                        tracksList.add(tInfo);
                    }
                    data.put("tracks", tracksList);
                    return data;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, state);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TransportHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                String action = (String) params.get("action");

                Map<String, Object> res = runOnBitwigThread(() -> {
                    Transport transport = extension.getTransport();
                    Map<String, Object> r = new LinkedHashMap<>();
                    if ("play".equalsIgnoreCase(action)) {
                        transport.play();
                        r.put("action", "play");
                    } else if ("stop".equalsIgnoreCase(action)) {
                        transport.stop();
                        r.put("action", "stop");
                    } else if ("restart".equalsIgnoreCase(action)) {
                        transport.restart();
                        r.put("action", "restart");
                    } else if ("set_tempo".equalsIgnoreCase(action)) {
                        Number tempoNum = (Number) params.get("tempo");
                        if (tempoNum != null) {
                            transport.tempo().value().setRaw(tempoNum.doubleValue());
                            r.put("action", "set_tempo");
                            r.put("tempo", tempoNum.doubleValue());
                        }
                    } else if ("set_position".equalsIgnoreCase(action)) {
                        Number pos = (Number) params.get("position");
                        if (pos != null) {
                            transport.setPosition(pos.doubleValue());
                            r.put("action", "set_position");
                            r.put("position", pos.doubleValue());
                        }
                    } else if ("record".equalsIgnoreCase(action) || "start_record".equalsIgnoreCase(action)) {
                        transport.isArrangerRecordEnabled().set(true);
                        transport.play();
                        r.put("action", "record");
                    } else if ("stop_record".equalsIgnoreCase(action)) {
                        transport.isArrangerRecordEnabled().set(false);
                        r.put("action", "stop_record");
                    } else if ("toggle_record".equalsIgnoreCase(action)) {
                        transport.isArrangerRecordEnabled().toggle();
                        r.put("action", "toggle_record");
                    } else if ("return_to_arrangement".equalsIgnoreCase(action)) {
                        transport.returnToArrangement();
                        r.put("action", "return_to_arrangement");
                    } else {
                        r.put("error", "Unknown transport action: " + action);
                    }
                    r.put("isPlaying", transport.isPlaying().get());
                    r.put("isRecording", transport.isArrangerRecordEnabled().get());
                    r.put("current_tempo", transport.tempo().value().getRaw());
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TrackSelectHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Number trackIdxNum = (Number) params.get("track");
                int trackIdx = trackIdxNum != null ? trackIdxNum.intValue() : 0;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    extension.getCursorTrack().selectChannel(track);
                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("selected_track", trackIdx);
                    r.put("name", track.name().get());
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class ClipCreateHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                int slotIdx = params.containsKey("slot") ? ((Number) params.get("slot")).intValue() : 0;
                int beats = params.containsKey("beats") ? ((Number) params.get("beats")).intValue() : 16;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    extension.getCursorTrack().selectChannel(track);
                    ClipLauncherSlot slot = (ClipLauncherSlot) track.clipLauncherSlotBank().getItemAt(slotIdx);
                    slot.select();
                    slot.createEmptyClip(beats);
                    extension.getCursorClip().showInEditor();

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "created");
                    r.put("track", trackIdx);
                    r.put("slot", slotIdx);
                    r.put("beats", beats);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    @SuppressWarnings("unchecked")
    private class ClipNotesHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                int slotIdx = params.containsKey("slot") ? ((Number) params.get("slot")).intValue() : 0;
                int beats = params.containsKey("beats") ? ((Number) params.get("beats")).intValue() : 16;
                boolean clear = !params.containsKey("clear") || Boolean.TRUE.equals(params.get("clear"));
                List<Map<String, Object>> notes = (List<Map<String, Object>>) params.get("notes");
                if (notes == null) notes = Collections.emptyList();

                final List<Map<String, Object>> notesList = notes;

                CompletableFuture<Map<String, Object>> taskFuture = new CompletableFuture<>();
                host.scheduleTask(() -> {
                    try {
                        Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                        extension.getCursorTrack().selectChannel(track);
                        track.selectInMixer();

                        ClipLauncherSlot slot = (ClipLauncherSlot) track.clipLauncherSlotBank().getItemAt(slotIdx);
                        slot.select();
                        slot.showInEditor();

                        boolean needsCreation = !slot.hasContent().get();
                        if (needsCreation) {
                            slot.createEmptyClip(beats);
                            slot.select();
                            slot.showInEditor();
                        }

                        // Delay allows Bitwig engine to register the new clip and attach cursorClip
                        long delay = needsCreation ? 200 : 50;
                        host.scheduleTask(() -> {
                            try {
                                slot.select();
                                slot.showInEditor();

                                PinnableCursorClip cursorClip = extension.getCursorClip();
                                cursorClip.scrollToStep(0);

                                if (clear) {
                                    cursorClip.clearSteps();
                                }

                                // Update clip boundaries and loop length to match beats
                                try {
                                    double targetBeats = (double) beats;
                                    double currentPlayStop = 16.0;
                                    try { currentPlayStop = cursorClip.getPlayStop().get(); } catch (Throwable ignored) {}
                                    if (targetBeats >= currentPlayStop) {
                                        cursorClip.getPlayStop().set(targetBeats);
                                        cursorClip.getLoopLength().set(targetBeats);
                                    } else {
                                        cursorClip.getLoopLength().set(targetBeats);
                                        cursorClip.getPlayStop().set(targetBeats);
                                    }
                                    cursorClip.getPlayStart().set(0.0);
                                    cursorClip.getLoopStart().set(0.0);
                                    cursorClip.isLoopEnabled().set(true);
                                } catch (Throwable ignored) {}

                                int count = 0;
                                for (Map<String, Object> n : notesList) {
                                    int step = ((Number) n.get("step")).intValue();
                                    int pitch = ((Number) n.get("pitch")).intValue();
                                    int velocity = n.containsKey("velocity") ? ((Number) n.get("velocity")).intValue() : 100;
                                    double duration = n.containsKey("duration") ? ((Number) n.get("duration")).doubleValue() : 1.0;
                                    int channel = n.containsKey("channel") ? ((Number) n.get("channel")).intValue() : 0;

                                    pitch = Math.max(0, Math.min(127, pitch));
                                    velocity = Math.max(1, Math.min(127, velocity));
                                    duration = Math.max(0.05, duration);

                                    if (step >= 0 && step < BitwigAgentExtension.GRID_STEPS) {
                                        cursorClip.setStep(channel, step, pitch, velocity, duration);
                                        count++;
                                    }
                                }

                                cursorClip.showInEditor();

                                Map<String, Object> r = new LinkedHashMap<>();
                                r.put("status", "notes_written");
                                r.put("track", trackIdx);
                                r.put("slot", slotIdx);
                                r.put("notes_count", count);
                                taskFuture.complete(r);
                            } catch (Throwable t) {
                                taskFuture.completeExceptionally(t);
                            }
                        }, delay);
                    } catch (Throwable t) {
                        taskFuture.completeExceptionally(t);
                    }
                }, 0);

                Map<String, Object> res = taskFuture.get(10, TimeUnit.SECONDS);
                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class ClipClearHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                int slotIdx = params.containsKey("slot") ? ((Number) params.get("slot")).intValue() : 0;
                String action = params.containsKey("action") ? (String) params.get("action") : "notes";

                Map<String, Object> res = runOnBitwigThread(() -> {
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    extension.getCursorTrack().selectChannel(track);
                    ClipLauncherSlot slot = (ClipLauncherSlot) track.clipLauncherSlotBank().getItemAt(slotIdx);
                    slot.select();

                    if ("delete".equalsIgnoreCase(action)) {
                        slot.deleteObject();
                    } else {
                        extension.getCursorClip().clearSteps();
                    }

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "cleared");
                    r.put("action", action);
                    r.put("track", trackIdx);
                    r.put("slot", slotIdx);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class ClipLaunchHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                int slotIdx = params.containsKey("slot") ? ((Number) params.get("slot")).intValue() : 0;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    ClipLauncherSlot slot = (ClipLauncherSlot) track.clipLauncherSlotBank().getItemAt(slotIdx);
                    slot.launch();

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "launched");
                    r.put("track", trackIdx);
                    r.put("slot", slotIdx);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class SceneLaunchHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int sceneIdx = params.containsKey("scene") ? ((Number) params.get("scene")).intValue() : 0;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    extension.getTrackBank().launchScene(sceneIdx);

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "launched");
                    r.put("scene", sceneIdx);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private static final Map<String, UUID> BITWIG_DEVICES = new LinkedHashMap<>();
    static {
        // Synths & Instruments
        BITWIG_DEVICES.put("polymer", UUID.fromString("8f58138b-03aa-4e9d-83bd-a038c99a4ed5"));
        BITWIG_DEVICES.put("polysynth", UUID.fromString("a9ffacb5-33e9-4fc7-8621-b1af31e410ef"));
        BITWIG_DEVICES.put("fm-4", UUID.fromString("7a0a94df-3aa4-4bb5-8e24-2511999871ad"));
        BITWIG_DEVICES.put("fm4", UUID.fromString("7a0a94df-3aa4-4bb5-8e24-2511999871ad"));
        BITWIG_DEVICES.put("phase-4", UUID.fromString("252723bf-68a6-4ee6-81f8-95ba4d0fb467"));
        BITWIG_DEVICES.put("phase4", UUID.fromString("252723bf-68a6-4ee6-81f8-95ba4d0fb467"));
        BITWIG_DEVICES.put("sampler", UUID.fromString("468bc14b-b2e7-45a1-9666-e83117fe404e"));
        BITWIG_DEVICES.put("drum_machine", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_DEVICES.put("drummachine", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_DEVICES.put("drums", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_DEVICES.put("organ", UUID.fromString("f2dcfe9a-7b66-4c84-984a-b25685a1c21a"));
        BITWIG_DEVICES.put("poly_grid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_DEVICES.put("polygrid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_DEVICES.put("the_grid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_DEVICES.put("instrument_layer", UUID.fromString("5024be2e-65d6-4d40-bbfe-8b2ea993c445"));

        // Reverb & Delay
        BITWIG_DEVICES.put("reverb", UUID.fromString("5a1cb339-1c4a-4cc7-9cae-bd7a2058153d"));
        BITWIG_DEVICES.put("delay+", UUID.fromString("f2baa2a8-36c5-4a79-b1d9-a4e461c45ee9"));
        BITWIG_DEVICES.put("delayplus", UUID.fromString("f2baa2a8-36c5-4a79-b1d9-a4e461c45ee9"));
        BITWIG_DEVICES.put("delay-1", UUID.fromString("2a7a7328-3f7a-4afb-95eb-5230c298bb90"));
        BITWIG_DEVICES.put("delay1", UUID.fromString("2a7a7328-3f7a-4afb-95eb-5230c298bb90"));
        BITWIG_DEVICES.put("delay-2", UUID.fromString("71539d5d-1c7a-4dac-8f74-29e23b89b599"));
        BITWIG_DEVICES.put("delay2", UUID.fromString("71539d5d-1c7a-4dac-8f74-29e23b89b599"));
        BITWIG_DEVICES.put("delay", UUID.fromString("71539d5d-1c7a-4dac-8f74-29e23b89b599"));
        BITWIG_DEVICES.put("delay-4", UUID.fromString("f95a0e18-5a8b-4f53-93ad-8be73fd668bd"));
        BITWIG_DEVICES.put("delay4", UUID.fromString("f95a0e18-5a8b-4f53-93ad-8be73fd668bd"));

        // Dynamics
        BITWIG_DEVICES.put("compressor", UUID.fromString("2b1b4787-8d74-4138-877b-9197209eef0f"));
        BITWIG_DEVICES.put("comp", UUID.fromString("2b1b4787-8d74-4138-877b-9197209eef0f"));
        BITWIG_DEVICES.put("compressor+", UUID.fromString("42b32cd2-6275-4ff1-970f-4fac71d15ad9"));
        BITWIG_DEVICES.put("compressorplus", UUID.fromString("42b32cd2-6275-4ff1-970f-4fac71d15ad9"));
        BITWIG_DEVICES.put("dynamics", UUID.fromString("22e785a2-a187-41e9-a0f2-66343694014c"));
        BITWIG_DEVICES.put("gate", UUID.fromString("556300ac-3a6e-4423-966a-5d5dde459a1b"));
        BITWIG_DEVICES.put("peak_limiter", UUID.fromString("8da7251e-2578-4bcc-b3c4-8f4ec2e115d0"));
        BITWIG_DEVICES.put("limiter", UUID.fromString("8da7251e-2578-4bcc-b3c4-8f4ec2e115d0"));
        BITWIG_DEVICES.put("de-esser", UUID.fromString("8750db61-e9d3-4d0e-a610-e734006a64dc"));
        BITWIG_DEVICES.put("deesser", UUID.fromString("8750db61-e9d3-4d0e-a610-e734006a64dc"));
        BITWIG_DEVICES.put("transient_control", UUID.fromString("71e6dbd8-a117-4ff0-85e8-5650f5a76d98"));
        BITWIG_DEVICES.put("transient", UUID.fromString("71e6dbd8-a117-4ff0-85e8-5650f5a76d98"));

        // EQ & Filters
        BITWIG_DEVICES.put("eq+", UUID.fromString("e4815188-ba6f-4d14-bcfc-2dcb8f778ccb"));
        BITWIG_DEVICES.put("eqplus", UUID.fromString("e4815188-ba6f-4d14-bcfc-2dcb8f778ccb"));
        BITWIG_DEVICES.put("eq", UUID.fromString("e4815188-ba6f-4d14-bcfc-2dcb8f778ccb"));
        BITWIG_DEVICES.put("eq-5", UUID.fromString("227e2e3c-75d5-46f3-960d-8fb5529fe29f"));
        BITWIG_DEVICES.put("eq5", UUID.fromString("227e2e3c-75d5-46f3-960d-8fb5529fe29f"));
        BITWIG_DEVICES.put("eq-2", UUID.fromString("01af068e-1e49-4777-a6e6-7f1dc679227a"));
        BITWIG_DEVICES.put("eq2", UUID.fromString("01af068e-1e49-4777-a6e6-7f1dc679227a"));
        BITWIG_DEVICES.put("eq-dj", UUID.fromString("3cc1b71a-e22a-42cf-89f0-316475368fb3"));
        BITWIG_DEVICES.put("eqdj", UUID.fromString("3cc1b71a-e22a-42cf-89f0-316475368fb3"));
        BITWIG_DEVICES.put("filter", UUID.fromString("4ccfc70e-59bd-4e97-a8a7-d8cdce88bf42"));
        BITWIG_DEVICES.put("filter+", UUID.fromString("6d621c1c-ab64-43b4-aea3-dad37e6f649c"));
        BITWIG_DEVICES.put("filterplus", UUID.fromString("6d621c1c-ab64-43b4-aea3-dad37e6f649c"));
        BITWIG_DEVICES.put("ladder", UUID.fromString("abfbbd63-8801-4bdb-a1ad-4b197f4d41e0"));
        BITWIG_DEVICES.put("sweep", UUID.fromString("ab52804f-1169-4657-b8c8-8db5532cf717"));
        BITWIG_DEVICES.put("comb", UUID.fromString("20e18780-8438-48d3-b234-40dcbaa947b8"));
        BITWIG_DEVICES.put("resonator_bank", UUID.fromString("b64070ae-5a59-4640-bb6a-194619bc12d8"));
        BITWIG_DEVICES.put("resonator", UUID.fromString("b64070ae-5a59-4640-bb6a-194619bc12d8"));
        BITWIG_DEVICES.put("tilt", UUID.fromString("061dcec6-543f-46f6-b679-f092eeefdbe4"));
        BITWIG_DEVICES.put("focus", UUID.fromString("42208fc5-02fd-42b4-9681-a8fadb46575f"));
        BITWIG_DEVICES.put("sculpt", UUID.fromString("8d9d63db-9991-4e46-8b4c-77755d1fcaab"));

        // Distortion & Saturation
        BITWIG_DEVICES.put("saturator", UUID.fromString("93d11348-86ae-4ead-9fe7-84ac03b9369c"));
        BITWIG_DEVICES.put("sat", UUID.fromString("93d11348-86ae-4ead-9fe7-84ac03b9369c"));
        BITWIG_DEVICES.put("distortion", UUID.fromString("b5b2b08e-730e-4192-be71-f572ceb5069b"));
        BITWIG_DEVICES.put("dist", UUID.fromString("b5b2b08e-730e-4192-be71-f572ceb5069b"));
        BITWIG_DEVICES.put("amp", UUID.fromString("41be8f3a-6d24-4442-9508-8548dbe62d47"));
        BITWIG_DEVICES.put("bit-8", UUID.fromString("43875255-6f1f-4d54-a5ad-c45bff793477"));
        BITWIG_DEVICES.put("bit8", UUID.fromString("43875255-6f1f-4d54-a5ad-c45bff793477"));
        BITWIG_DEVICES.put("over", UUID.fromString("41b34699-8e5d-4534-a429-a67d488ba6ac"));

        // Modulation
        BITWIG_DEVICES.put("chorus", UUID.fromString("d275f9a6-0e4a-409c-9dc4-d74af90bc7ae"));
        BITWIG_DEVICES.put("chorus+", UUID.fromString("1b8f2226-c432-4a0a-9830-69bc76d1a276"));
        BITWIG_DEVICES.put("chorusplus", UUID.fromString("1b8f2226-c432-4a0a-9830-69bc76d1a276"));
        BITWIG_DEVICES.put("flanger", UUID.fromString("8393c436-b11b-4fee-85dd-b2ef0a2ed380"));
        BITWIG_DEVICES.put("flanger+", UUID.fromString("a99f8c3c-7813-4e6b-a18a-302c74286efc"));
        BITWIG_DEVICES.put("flangerplus", UUID.fromString("a99f8c3c-7813-4e6b-a18a-302c74286efc"));
        BITWIG_DEVICES.put("phaser", UUID.fromString("fc87ae07-1624-449f-8dae-2db5d93e1aa9"));
        BITWIG_DEVICES.put("phaser+", UUID.fromString("fd7a9e6c-6992-40c2-be3b-ac8ed48553e9"));
        BITWIG_DEVICES.put("phaserplus", UUID.fromString("fd7a9e6c-6992-40c2-be3b-ac8ed48553e9"));
        BITWIG_DEVICES.put("tremolo", UUID.fromString("f3b90fff-402b-4187-9aab-620f441577b9"));
        BITWIG_DEVICES.put("rotary", UUID.fromString("8fc25e70-b92b-4096-8270-42e492df501a"));

        // Utility, Pitch & Spatial
        BITWIG_DEVICES.put("tool", UUID.fromString("e67b9c56-838d-4fba-8e3e-ae4e02cccbcb"));
        BITWIG_DEVICES.put("dual_pan", UUID.fromString("c94820f8-3779-438b-a85b-868e57b746cc"));
        BITWIG_DEVICES.put("dualpan", UUID.fromString("c94820f8-3779-438b-a85b-868e57b746cc"));
        BITWIG_DEVICES.put("time_shift", UUID.fromString("861bb5b0-5cd6-4066-9681-1cc561cb898f"));
        BITWIG_DEVICES.put("pitch_shifter", UUID.fromString("384fe469-6023-4f69-9560-e0c2eec2da49"));
        BITWIG_DEVICES.put("freq_shifter", UUID.fromString("7ec87fdf-0bf8-42e7-b54b-5d8b68e330b1"));
        BITWIG_DEVICES.put("freq_shifter+", UUID.fromString("eb28831d-2478-4918-bd51-bcc1ff4c7eed"));
        BITWIG_DEVICES.put("ring_mod", UUID.fromString("374feaeb-c785-4243-9d08-3f9099b4c0cb"));
        BITWIG_DEVICES.put("ringmod", UUID.fromString("374feaeb-c785-4243-9d08-3f9099b4c0cb"));
        BITWIG_DEVICES.put("blur", UUID.fromString("72a3018d-788b-472c-b1d7-16419d00f4c6"));
        BITWIG_DEVICES.put("treemonster", UUID.fromString("e45e00d2-85a0-4c05-8321-819694befa09"));
        BITWIG_DEVICES.put("vocoder", UUID.fromString("a0cb2ec0-2464-461c-8165-296f98905539"));
        BITWIG_DEVICES.put("spectrum", UUID.fromString("fcd9aa65-ebbb-4337-a97e-69929322ef47"));
        BITWIG_DEVICES.put("oscilloscope", UUID.fromString("ffe670a2-09aa-4c9b-8822-5161a9cca686"));
    }

    private static UUID resolveDeviceUuid(String nameOrUuid) {
        if (nameOrUuid == null || nameOrUuid.trim().isEmpty()) {
            return null;
        }
        String key = nameOrUuid.trim().toLowerCase(Locale.ROOT);
        if (BITWIG_DEVICES.containsKey(key)) {
            return BITWIG_DEVICES.get(key);
        }
        String altKey = key.replace("-", "_").replace(" ", "_");
        if (BITWIG_DEVICES.containsKey(altKey)) {
            return BITWIG_DEVICES.get(altKey);
        }
        String noDash = key.replace("-", "").replace("_", "").replace(" ", "");
        if (BITWIG_DEVICES.containsKey(noDash)) {
            return BITWIG_DEVICES.get(noDash);
        }
        try {
            return UUID.fromString(nameOrUuid.trim());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private static UUID resolveInstrumentUuid(String nameOrUuid) {
        return resolveDeviceUuid(nameOrUuid);
    }

    private class InstrumentAddHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                String name = (String) params.get("name");
                String instrumentStr = (String) params.get("instrument");
                Number trackNum = (Number) params.get("track");
                Number posNum = (Number) params.get("position");

                final UUID uuid = resolveInstrumentUuid(instrumentStr);
                final String finalName = name;
                final String finalInstrument = instrumentStr;

                CompletableFuture<Map<String, Object>> taskFuture = new CompletableFuture<>();

                if (trackNum != null && trackNum.intValue() >= 0) {
                    final int trackIdx = trackNum.intValue();
                    host.scheduleTask(() -> {
                        try {
                            Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                            extension.getCursorTrack().selectChannel(track);
                            if (finalName != null && !finalName.trim().isEmpty()) {
                                track.setName(finalName);
                            }
                            if (uuid != null) {
                                track.endOfDeviceChainInsertionPoint().insertBitwigDevice(uuid);
                            } else if (finalInstrument != null && (finalInstrument.endsWith(".bwpreset") || finalInstrument.endsWith(".bwdevice"))) {
                                track.endOfDeviceChainInsertionPoint().insertFile(finalInstrument);
                            }
                            Map<String, Object> r = new LinkedHashMap<>();
                            r.put("status", "instrument_added");
                            r.put("track", trackIdx);
                            r.put("name", finalName != null ? finalName : track.name().get());
                            r.put("instrument", finalInstrument);
                            taskFuture.complete(r);
                        } catch (Throwable t) {
                            taskFuture.completeExceptionally(t);
                        }
                    }, 0);
                } else {
                    final int pos = posNum != null ? posNum.intValue() : -1;
                    host.scheduleTask(() -> {
                        try {
                            extension.getApplication().createInstrumentTrack(pos);
                            host.scheduleTask(() -> {
                                try {
                                    CursorTrack cursorTrack = extension.getCursorTrack();
                                    if (finalName != null && !finalName.trim().isEmpty()) {
                                        cursorTrack.setName(finalName);
                                    }
                                    if (uuid != null) {
                                        cursorTrack.endOfDeviceChainInsertionPoint().insertBitwigDevice(uuid);
                                    } else if (finalInstrument != null && (finalInstrument.endsWith(".bwpreset") || finalInstrument.endsWith(".bwdevice"))) {
                                        cursorTrack.endOfDeviceChainInsertionPoint().insertFile(finalInstrument);
                                    }
                                    Map<String, Object> r = new LinkedHashMap<>();
                                    r.put("status", "created");
                                    r.put("name", finalName != null ? finalName : cursorTrack.name().get());
                                    r.put("instrument", finalInstrument);
                                    r.put("uuid", uuid != null ? uuid.toString() : null);
                                    taskFuture.complete(r);
                                } catch (Throwable t) {
                                    taskFuture.completeExceptionally(t);
                                }
                            }, 150);
                        } catch (Throwable t) {
                            taskFuture.completeExceptionally(t);
                        }
                    }, 0);
                }

                Map<String, Object> res = taskFuture.get(5, TimeUnit.SECONDS);
                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class EffectAddHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                String effectStr = (String) params.get("effect");
                Number trackNum = (Number) params.get("track");
                Object posObj = params.get("position");
                boolean createEffectTrack = Boolean.TRUE.equals(params.get("create_effect_track"));

                final UUID uuid = resolveDeviceUuid(effectStr);
                final String finalEffect = effectStr;

                CompletableFuture<Map<String, Object>> taskFuture = new CompletableFuture<>();

                if (createEffectTrack) {
                    host.scheduleTask(() -> {
                        try {
                            extension.getApplication().createEffectTrack(-1);
                            host.scheduleTask(() -> {
                                try {
                                    CursorTrack cursorTrack = extension.getCursorTrack();
                                    if (uuid != null) {
                                        cursorTrack.endOfDeviceChainInsertionPoint().insertBitwigDevice(uuid);
                                    } else if (finalEffect != null && (finalEffect.endsWith(".bwpreset") || finalEffect.endsWith(".bwdevice"))) {
                                        cursorTrack.endOfDeviceChainInsertionPoint().insertFile(finalEffect);
                                    }
                                    Map<String, Object> r = new LinkedHashMap<>();
                                    r.put("status", "effect_track_created");
                                    r.put("effect", finalEffect);
                                    r.put("uuid", uuid != null ? uuid.toString() : null);
                                    taskFuture.complete(r);
                                } catch (Throwable t) {
                                    taskFuture.completeExceptionally(t);
                                }
                            }, 150);
                        } catch (Throwable t) {
                            taskFuture.completeExceptionally(t);
                        }
                    }, 0);
                } else {
                    final int trackIdx = trackNum != null ? trackNum.intValue() : 0;
                    host.scheduleTask(() -> {
                        try {
                            Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                            extension.getCursorTrack().selectChannel(track);

                            InsertionPoint insertionPoint = null;
                            if (posObj instanceof Number) {
                                int devIdx = ((Number) posObj).intValue();
                                DeviceBank devBank = extension.getDeviceBank(trackIdx);
                                if (devBank != null && devIdx >= 0 && devIdx < 16) {
                                    Device targetDev = devBank.getDevice(devIdx);
                                    if (targetDev.exists().get()) {
                                        insertionPoint = targetDev.afterDeviceInsertionPoint();
                                    }
                                }
                            } else if ("start".equalsIgnoreCase(String.valueOf(posObj))) {
                                insertionPoint = track.startOfDeviceChainInsertionPoint();
                            }

                            if (insertionPoint == null) {
                                insertionPoint = track.endOfDeviceChainInsertionPoint();
                            }

                            if (uuid != null) {
                                insertionPoint.insertBitwigDevice(uuid);
                            } else if (finalEffect != null && (finalEffect.endsWith(".bwpreset") || finalEffect.endsWith(".bwdevice"))) {
                                insertionPoint.insertFile(finalEffect);
                            }

                            Map<String, Object> r = new LinkedHashMap<>();
                            r.put("status", "effect_added");
                            r.put("track", trackIdx);
                            r.put("track_name", track.name().get());
                            r.put("effect", finalEffect);
                            r.put("position", String.valueOf(posObj != null ? posObj : "end"));
                            r.put("uuid", uuid != null ? uuid.toString() : null);
                            taskFuture.complete(r);
                        } catch (Throwable t) {
                            taskFuture.completeExceptionally(t);
                        }
                    }, 0);
                }

                Map<String, Object> res = taskFuture.get(5, TimeUnit.SECONDS);
                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class DeviceControlHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                Object devObj = params.get("device");
                String action = (String) params.get("action");
                Boolean enabledParam = params.containsKey("enabled") ? (Boolean) params.get("enabled") : null;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    DeviceBank devBank = extension.getDeviceBank(trackIdx);
                    if (devBank == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Track index out of range: " + trackIdx);
                        return err;
                    }

                    Device targetDev = null;
                    int targetIdx = -1;

                    if (devObj instanceof Number) {
                        targetIdx = ((Number) devObj).intValue();
                        if (targetIdx >= 0 && targetIdx < 16) {
                            Device d = devBank.getDevice(targetIdx);
                            if (d.exists().get()) {
                                targetDev = d;
                            }
                        }
                    } else if (devObj instanceof String) {
                        String nameQuery = ((String) devObj).trim().toLowerCase(Locale.ROOT);
                        if (nameQuery.matches("\\d+")) {
                            int idx = Integer.parseInt(nameQuery);
                            if (idx >= 0 && idx < 16 && devBank.getDevice(idx).exists().get()) {
                                targetDev = devBank.getDevice(idx);
                                targetIdx = idx;
                            }
                        }
                        if (targetDev == null) {
                            for (int d = 0; d < 16; d++) {
                                Device dev = devBank.getDevice(d);
                                if (dev.exists().get() && dev.name().get().toLowerCase(Locale.ROOT).contains(nameQuery)) {
                                    targetDev = dev;
                                    targetIdx = d;
                                    break;
                                }
                            }
                        }
                    }

                    if (targetDev == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Device not found on track " + trackIdx + ": " + devObj);
                        return err;
                    }

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("track", trackIdx);
                    r.put("device_index", targetIdx);
                    r.put("device_name", targetDev.name().get());
                    r.put("action", action);

                    if ("set_enabled".equalsIgnoreCase(action)) {
                        boolean en = enabledParam != null ? enabledParam : true;
                        targetDev.isEnabled().set(en);
                        r.put("isEnabled", en);
                    } else if ("toggle".equalsIgnoreCase(action)) {
                        targetDev.isEnabled().toggle();
                        r.put("toggled", true);
                    } else if ("delete".equalsIgnoreCase(action) || "remove".equalsIgnoreCase(action)) {
                        targetDev.deleteObject();
                        r.put("deleted", true);
                    } else if ("next_preset".equalsIgnoreCase(action)) {
                        targetDev.switchToNextPreset();
                        r.put("switched", "next_preset");
                    } else if ("previous_preset".equalsIgnoreCase(action)) {
                        targetDev.switchToPreviousPreset();
                        r.put("switched", "previous_preset");
                    } else if ("toggle_window".equalsIgnoreCase(action) || "toggle_window_open".equalsIgnoreCase(action)) {
                        targetDev.isWindowOpen().toggle();
                        r.put("window_toggled", true);
                    } else if ("open_window".equalsIgnoreCase(action)) {
                        targetDev.isWindowOpen().set(true);
                        r.put("window_open", true);
                    } else if ("close_window".equalsIgnoreCase(action)) {
                        targetDev.isWindowOpen().set(false);
                        r.put("window_open", false);
                    } else if ("select".equalsIgnoreCase(action)) {
                        targetDev.selectInEditor();
                        r.put("selected", true);
                    } else {
                        r.put("error", "Unknown device action: " + action);
                    }

                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class DeviceParameterHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                int trackIdx = params.containsKey("track") ? ((Number) params.get("track")).intValue() : 0;
                Object devObj = params.get("device");
                String parameter = (String) params.get("parameter");
                Number valueNum = (Number) params.get("value");

                Map<String, Object> res = runOnBitwigThread(() -> {
                    DeviceBank devBank = extension.getDeviceBank(trackIdx);
                    if (devBank == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Track index out of range: " + trackIdx);
                        return err;
                    }

                    Device targetDev = null;
                    int targetIdx = -1;

                    if (devObj instanceof Number) {
                        targetIdx = ((Number) devObj).intValue();
                        if (targetIdx >= 0 && targetIdx < 16) {
                            Device d = devBank.getDevice(targetIdx);
                            if (d.exists().get()) targetDev = d;
                        }
                    } else if (devObj instanceof String) {
                        String nameQuery = ((String) devObj).trim().toLowerCase(Locale.ROOT);
                        for (int d = 0; d < 16; d++) {
                            Device dev = devBank.getDevice(d);
                            if (dev.exists().get() && dev.name().get().toLowerCase(Locale.ROOT).contains(nameQuery)) {
                                targetDev = dev;
                                targetIdx = d;
                                break;
                            }
                        }
                    }

                    if (targetDev == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Device not found on track " + trackIdx + ": " + devObj);
                        return err;
                    }
                    if (parameter == null || parameter.trim().isEmpty()) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Missing 'parameter' name.");
                        return err;
                    }
                    if (valueNum == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Missing 'value' to set.");
                        return err;
                    }

                    CursorRemoteControlsPage remotes = extension.getRemoteControlsPage(trackIdx, targetIdx);
                    if (remotes == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Remote controls page not available for device " + targetIdx + " on track " + trackIdx);
                        return err;
                    }

                    // Optional page selection
                    String pageParam = (String) params.get("page");
                    if (pageParam != null && !pageParam.trim().isEmpty()) {
                        remotes.selectNextPageMatching(pageParam.trim(), true);
                    }

                    String paramQuery = parameter.trim().toLowerCase(Locale.ROOT);
                    RemoteControl matchedControl = null;
                    int matchedIndex = -1;

                    // Strategy 1: Check if parameter is specified as integer index ("0", 0, "1", etc.)
                    try {
                        int pIdx = Integer.parseInt(paramQuery);
                        if (pIdx >= 0 && pIdx < 8) {
                            matchedControl = remotes.getParameter(pIdx);
                            matchedIndex = pIdx;
                        }
                    } catch (NumberFormatException ignored) {}

                    // Strategy 2: Exact name match (case-insensitive)
                    if (matchedControl == null) {
                        for (int p = 0; p < 8; p++) {
                            RemoteControl rc = remotes.getParameter(p);
                            String pName = rc.name().get();
                            if (pName != null && pName.equalsIgnoreCase(paramQuery)) {
                                matchedControl = rc;
                                matchedIndex = p;
                                break;
                            }
                        }
                    }

                    // Strategy 3: Normalized name match (ignoring spaces/underscores/dashes, e.g. "lowfreq" == "Low Freq")
                    if (matchedControl == null) {
                        String cleanQuery = paramQuery.replaceAll("[\\s_\\-]+", "");
                        for (int p = 0; p < 8; p++) {
                            RemoteControl rc = remotes.getParameter(p);
                            String pName = rc.name().get();
                            if (pName != null && pName.toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-]+", "").equals(cleanQuery)) {
                                matchedControl = rc;
                                matchedIndex = p;
                                break;
                            }
                        }
                    }

                    // Strategy 4: Substring containment (e.g. "freq", "gain", "cutoff", "res")
                    if (matchedControl == null) {
                        for (int p = 0; p < 8; p++) {
                            RemoteControl rc = remotes.getParameter(p);
                            String pName = rc.name().get();
                            if (pName != null && pName.toLowerCase(Locale.ROOT).contains(paramQuery)) {
                                matchedControl = rc;
                                matchedIndex = p;
                                break;
                            }
                        }
                    }

                    if (matchedControl == null) {
                        List<String> available = new ArrayList<>();
                        for (int p = 0; p < 8; p++) {
                            String name = remotes.getParameter(p).name().get();
                            if (name != null && !name.trim().isEmpty()) {
                                available.add("[" + p + "] " + name);
                            }
                        }
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Parameter '" + parameter + "' not found on device '" + targetDev.name().get() + "'. Available parameters on current page: " + available);
                        err.put("available_parameters", available);
                        return err;
                    }

                    try {
                        double val = valueNum.doubleValue();
                        // If normalized is requested or value is within 0.0 - 1.0, set normalized; also allow raw set
                        boolean normalized = Boolean.TRUE.equals(params.get("normalized"));
                        if (normalized) {
                            matchedControl.value().set(val);
                        } else {
                            try {
                                matchedControl.value().setRaw(val);
                            } catch (Throwable fallback) {
                                matchedControl.value().set(val);
                            }
                        }

                        Map<String, Object> r = new LinkedHashMap<>();
                        r.put("status", "success");
                        r.put("track", trackIdx);
                        r.put("device_index", targetIdx);
                        r.put("device_name", targetDev.name().get());
                        r.put("parameter_index", matchedIndex);
                        r.put("parameter", matchedControl.name().get());
                        r.put("target_value", val);
                        r.put("displayed_value", matchedControl.displayedValue().get());
                        r.put("current_value", matchedControl.value().get());
                        return r;
                    } catch (Throwable t) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Failed to set parameter: " + t.getMessage());
                        return err;
                    }
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TrackInspectHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                Object trackParam = null;
                if ("GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                    String query = exchange.getRequestURI().getQuery();
                    if (query != null) {
                        for (String param : query.split("&")) {
                            String[] pair = param.split("=");
                            if (pair.length == 2 && "track".equalsIgnoreCase(pair[0])) {
                                trackParam = java.net.URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
                            }
                        }
                    }
                } else {
                    String body = readBody(exchange);
                    if (body != null && !body.trim().isEmpty()) {
                        Map<String, Object> params = JsonUtils.parseObject(body);
                        trackParam = params.get("track");
                    }
                }

                final Object finalTrackParam = trackParam != null ? trackParam : 0;

                Map<String, Object> res = runOnBitwigThread(() -> {
                    TrackBank bank = extension.getTrackBank();
                    int size = bank.getSizeOfBank();
                    int targetIdx = -1;

                    if (finalTrackParam instanceof Number) {
                        targetIdx = ((Number) finalTrackParam).intValue();
                    } else {
                        String str = finalTrackParam.toString().trim();
                        try {
                            targetIdx = Integer.parseInt(str);
                        } catch (NumberFormatException e) {
                            for (int i = 0; i < size; i++) {
                                Track t = (Track) bank.getItemAt(i);
                                if (t.exists().get() && t.name().get().equalsIgnoreCase(str)) {
                                    targetIdx = i;
                                    break;
                                }
                            }
                            if (targetIdx == -1) {
                                for (int i = 0; i < size; i++) {
                                    Track t = (Track) bank.getItemAt(i);
                                    if (t.exists().get() && t.name().get().toLowerCase().contains(str.toLowerCase())) {
                                        targetIdx = i;
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    if (targetIdx < 0 || targetIdx >= size) {
                        Map<String, Object> notFound = new LinkedHashMap<>();
                        notFound.put("error", "Track not found: " + finalTrackParam);
                        return notFound;
                    }

                    Track t = (Track) bank.getItemAt(targetIdx);
                    if (!t.exists().get()) {
                        Map<String, Object> notFound = new LinkedHashMap<>();
                        notFound.put("error", "Track at index " + targetIdx + " does not exist.");
                        return notFound;
                    }

                    Map<String, Object> tInfo = new LinkedHashMap<>();
                    tInfo.put("index", targetIdx);
                    tInfo.put("name", t.name().get());
                    tInfo.put("type", t.trackType().get());
                    tInfo.put("volume", t.volume().displayedValue().get());
                    tInfo.put("pan", t.pan().displayedValue().get());
                    tInfo.put("isGroup", t.isGroup().get());
                    tInfo.put("arm", t.arm().get());
                    tInfo.put("mute", t.mute().get());
                    tInfo.put("solo", t.solo().get());

                    List<Map<String, Object>> devices = new ArrayList<>();
                    DeviceBank devBank = extension.getDeviceBank(targetIdx);
                    if (devBank != null) {
                        for (int d = 0; d < 16; d++) {
                            Device dev = devBank.getDevice(d);
                            if (!dev.exists().get()) continue;
                            Map<String, Object> dInfo = new LinkedHashMap<>();
                            dInfo.put("index", d);
                            dInfo.put("name", dev.name().get());
                            dInfo.put("type", dev.deviceType().get());
                            dInfo.put("preset", dev.presetName().get());
                            dInfo.put("category", dev.presetCategory().get());
                            dInfo.put("isEnabled", dev.isEnabled().get());
                            dInfo.put("isPlugin", dev.isPlugin().get());

                            CursorRemoteControlsPage remotes = extension.getRemoteControlsPage(targetIdx, d);
                            if (remotes != null) {
                                List<Map<String, Object>> paramsList = new ArrayList<>();
                                for (int p = 0; p < 8; p++) {
                                    RemoteControl rc = remotes.getParameter(p);
                                    String pName = rc.name().get();
                                    if (pName != null && !pName.trim().isEmpty()) {
                                        Map<String, Object> pInfo = new LinkedHashMap<>();
                                        pInfo.put("index", p);
                                        pInfo.put("name", pName);
                                        pInfo.put("value", rc.value().get());
                                        pInfo.put("displayed_value", rc.displayedValue().get());
                                        paramsList.add(pInfo);
                                    }
                                }
                                dInfo.put("parameters", paramsList);
                                String[] pages = remotes.pageNames().get();
                                if (pages != null) {
                                    dInfo.put("pages", Arrays.asList(pages));
                                }
                            }
                            devices.add(dInfo);
                        }
                    }
                    tInfo.put("devices", devices);

                    List<Map<String, Object>> slots = new ArrayList<>();
                    ClipLauncherSlotBank slotBank = t.clipLauncherSlotBank();
                    for (int s = 0; s < 16; s++) {
                        ClipLauncherSlot slot = (ClipLauncherSlot) slotBank.getItemAt(s);
                        if (!slot.hasContent().get()) continue;
                        Map<String, Object> sInfo = new LinkedHashMap<>();
                        sInfo.put("slot", s);
                        sInfo.put("name", slot.name().get());
                        sInfo.put("isPlaying", slot.isPlaying().get());
                        sInfo.put("isSelected", slot.isSelected().get());
                        slots.add(sInfo);
                    }
                    tInfo.put("occupied_clips", slots);

                    return tInfo;
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 404 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private static final String[] NOTE_PITCH_NAMES = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    private static String pitchToName(int pitch) {
        if (pitch < 0 || pitch > 127) return "Unknown";
        int octave = (pitch / 12) - 1;
        String name = NOTE_PITCH_NAMES[pitch % 12];
        return name + octave;
    }

    private class ClipInspectHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                Object trackParam = null;
                Object slotParam = null;
                if ("GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                    String query = exchange.getRequestURI().getQuery();
                    if (query != null) {
                        for (String param : query.split("&")) {
                            String[] pair = param.split("=");
                            if (pair.length == 2) {
                                if ("track".equalsIgnoreCase(pair[0])) {
                                    trackParam = java.net.URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
                                } else if ("slot".equalsIgnoreCase(pair[0])) {
                                    slotParam = java.net.URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
                                }
                            }
                        }
                    }
                } else {
                    String body = readBody(exchange);
                    if (body != null && !body.trim().isEmpty()) {
                        Map<String, Object> params = JsonUtils.parseObject(body);
                        trackParam = params.get("track");
                        slotParam = params.get("slot");
                    }
                }

                final Object finalTrackParam = trackParam != null ? trackParam : 0;
                int parsedSlot = 0;
                if (slotParam instanceof Number) {
                    parsedSlot = ((Number) slotParam).intValue();
                } else if (slotParam != null) {
                    try {
                        parsedSlot = Integer.parseInt(slotParam.toString().trim());
                    } catch (NumberFormatException ignored) {}
                }
                final int finalSlotIdx = Math.max(0, Math.min(15, parsedSlot));

                CompletableFuture<Map<String, Object>> future = new CompletableFuture<>();

                host.scheduleTask(() -> {
                    try {
                        TrackBank bank = extension.getTrackBank();
                        int size = bank.getSizeOfBank();
                        int targetIdx = -1;

                        if (finalTrackParam instanceof Number) {
                            targetIdx = ((Number) finalTrackParam).intValue();
                        } else {
                            String str = finalTrackParam.toString().trim();
                            try {
                                targetIdx = Integer.parseInt(str);
                            } catch (NumberFormatException e) {
                                for (int i = 0; i < size; i++) {
                                    Track t = (Track) bank.getItemAt(i);
                                    if (t.exists().get() && t.name().get().equalsIgnoreCase(str)) {
                                        targetIdx = i;
                                        break;
                                    }
                                }
                                if (targetIdx == -1) {
                                    for (int i = 0; i < size; i++) {
                                        Track t = (Track) bank.getItemAt(i);
                                        if (t.exists().get() && t.name().get().toLowerCase().contains(str.toLowerCase())) {
                                            targetIdx = i;
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        if (targetIdx < 0 || targetIdx >= size) {
                            Map<String, Object> notFound = new LinkedHashMap<>();
                            notFound.put("error", "Track not found: " + finalTrackParam);
                            future.complete(notFound);
                            return;
                        }

                        Track t = (Track) bank.getItemAt(targetIdx);
                        if (!t.exists().get()) {
                            Map<String, Object> notFound = new LinkedHashMap<>();
                            notFound.put("error", "Track at index " + targetIdx + " does not exist.");
                            future.complete(notFound);
                            return;
                        }

                        ClipLauncherSlotBank slotBank = t.clipLauncherSlotBank();
                        ClipLauncherSlot slot = (ClipLauncherSlot) slotBank.getItemAt(finalSlotIdx);
                        boolean hasContent = false;
                        try { hasContent = slot.hasContent().get(); } catch (Throwable ignored) {}
                        String clipName = "";
                        try { clipName = slot.name().get(); } catch (Throwable ignored) {}
                        boolean isPlaying = false;
                        try { isPlaying = slot.isPlaying().get(); } catch (Throwable ignored) {}
                        boolean isSelected = false;
                        try { isSelected = slot.isSelected().get(); } catch (Throwable ignored) {}
                        boolean isRecording = false;
                        try { isRecording = slot.isRecording().get(); } catch (Throwable ignored) {}

                        if (!hasContent) {
                            Map<String, Object> emptyResp = new LinkedHashMap<>();
                            emptyResp.put("track", targetIdx);
                            emptyResp.put("track_name", t.name().get());
                            emptyResp.put("track_type", t.trackType().get());
                            emptyResp.put("slot", finalSlotIdx);
                            emptyResp.put("name", clipName);
                            emptyResp.put("has_content", false);
                            emptyResp.put("is_playing", isPlaying);
                            emptyResp.put("is_selected", isSelected);
                            emptyResp.put("is_recording", isRecording);
                            emptyResp.put("message", "Clip slot is empty.");
                            emptyResp.put("notes", Collections.emptyList());
                            emptyResp.put("notes_count", 0);
                            future.complete(emptyResp);
                            return;
                        }

                        // Select track and slot to synchronize cursorClip
                        extension.getCursorTrack().selectChannel(t);
                        t.selectInMixer();
                        slot.select();
                        slot.showInEditor();

                        final int resolvedTrackIdx = targetIdx;
                        final String resolvedTrackName = t.name().get();
                        final String resolvedTrackType = t.trackType().get();
                        final String resolvedClipName = clipName;

                        // Give Bitwig engine brief delay to refresh cursorClip step cache
                        host.scheduleTask(() -> {
                            try {
                                PinnableCursorClip cursorClip = extension.getCursorClip();
                                cursorClip.scrollToStep(0);

                                double playStart = 0.0;
                                try { playStart = cursorClip.getPlayStart().get(); } catch (Throwable ignored) {}
                                double playStop = 16.0;
                                try { playStop = cursorClip.getPlayStop().get(); } catch (Throwable ignored) {}
                                boolean loopEnabled = true;
                                try { loopEnabled = cursorClip.isLoopEnabled().get(); } catch (Throwable ignored) {}
                                double loopStart = 0.0;
                                try { loopStart = cursorClip.getLoopStart().get(); } catch (Throwable ignored) {}
                                double loopLength = 16.0;
                                try { loopLength = cursorClip.getLoopLength().get(); } catch (Throwable ignored) {}
                                boolean shuffle = false;
                                try { shuffle = cursorClip.getShuffle().get(); } catch (Throwable ignored) {}
                                double accent = 0.0;
                                try { accent = cursorClip.getAccent().get(); } catch (Throwable ignored) {}
                                int playingStep = -1;
                                try { playingStep = cursorClip.playingStep().get(); } catch (Throwable ignored) {}

                                Map<String, Map<String, Object>> noteMap = new LinkedHashMap<>();

                                // 1. Read from extension step observer snapshots
                                for (BitwigAgentExtension.StepSnapshot snap : extension.getCurrentClipSteps().values()) {
                                    if (snap.state == 1) { // NoteOn
                                        String k = snap.x + ":" + snap.y;
                                        Map<String, Object> noteObj = new LinkedHashMap<>();
                                        noteObj.put("step", snap.x);
                                        noteObj.put("beat", snap.x * 0.25);
                                        noteObj.put("pitch", snap.y);
                                        noteObj.put("name", pitchToName(snap.y));
                                        noteObj.put("velocity", (int) Math.round(snap.velocity * 127.0));
                                        noteObj.put("duration", snap.duration);
                                        noteObj.put("channel", snap.channel);
                                        noteMap.put(k, noteObj);
                                    }
                                }

                                // 2. Also directly scan cursorClip steps for channel 0 up to active clip length
                                double scanBeats = Math.max(loopLength, playStop);
                                int maxScanStep = Math.min(BitwigAgentExtension.GRID_STEPS, Math.max(64, (int) Math.ceil(scanBeats * 4.0)));
                                for (int x = 0; x < maxScanStep; x++) {
                                    for (int y = 0; y < 128; y++) {
                                        NoteStep ns = cursorClip.getStep(0, x, y);
                                        if (ns != null && ns.state() != null && "NoteOn".equals(ns.state().name())) {
                                            String k = x + ":" + y;
                                            if (!noteMap.containsKey(k)) {
                                                Map<String, Object> noteObj = new LinkedHashMap<>();
                                                noteObj.put("step", x);
                                                noteObj.put("beat", x * 0.25);
                                                noteObj.put("pitch", y);
                                                noteObj.put("name", pitchToName(y));
                                                noteObj.put("velocity", (int) Math.round(ns.velocity() * 127.0));
                                                noteObj.put("duration", ns.duration());
                                                noteObj.put("channel", ns.channel());
                                                noteMap.put(k, noteObj);
                                            }
                                        }
                                    }
                                }

                                List<Map<String, Object>> notesList = new ArrayList<>(noteMap.values());
                                notesList.sort((a, b) -> {
                                    int sa = ((Number) a.get("step")).intValue();
                                    int sb = ((Number) b.get("step")).intValue();
                                    if (sa != sb) return Integer.compare(sa, sb);
                                    int pa = ((Number) a.get("pitch")).intValue();
                                    int pb = ((Number) b.get("pitch")).intValue();
                                    return Integer.compare(pa, pb);
                                });

                                Map<String, Object> r = new LinkedHashMap<>();
                                r.put("track", resolvedTrackIdx);
                                r.put("track_name", resolvedTrackName);
                                r.put("track_type", resolvedTrackType);
                                r.put("slot", finalSlotIdx);
                                r.put("name", resolvedClipName);
                                r.put("has_content", true);
                                r.put("is_playing", slot.isPlaying().get());
                                r.put("is_selected", slot.isSelected().get());
                                r.put("is_recording", slot.isRecording().get());
                                r.put("play_start", playStart);
                                r.put("play_stop", playStop);
                                r.put("loop_enabled", loopEnabled);
                                r.put("loop_start", loopStart);
                                r.put("loop_length", loopLength > 0 ? loopLength : 16.0);
                                r.put("shuffle", shuffle);
                                r.put("accent", accent);
                                r.put("playing_step", playingStep);
                                r.put("notes", notesList);
                                r.put("notes_count", notesList.size());

                                future.complete(r);
                            } catch (Throwable t2) {
                                future.completeExceptionally(t2);
                            }
                        }, 150);

                    } catch (Throwable t1) {
                        future.completeExceptionally(t1);
                    }
                }, 0);

                Map<String, Object> res = future.get(5, TimeUnit.SECONDS);
                int status = res.containsKey("error") ? 404 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class ArrangerInspectHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod()) && !"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJson(exchange, 405, Map.of("error", "Method Not Allowed"));
                return;
            }

            try {
                CompletableFuture<Map<String, Object>> future = new CompletableFuture<>();

                host.scheduleTask(() -> {
                    try {
                        Map<String, Object> res = new LinkedHashMap<>();
                        Transport transport = extension.getTransport();
                        Arranger arranger = extension.getArranger();
                        CueMarkerBank cueBank = extension.getCueMarkerBank();

                        // Arranger timeline / transport metrics
                        double playPosition = 0.0;
                        try { playPosition = transport.getPosition().get(); } catch (Throwable ignored) {}
                        double tempo = 120.0;
                        try { tempo = transport.tempo().value().getRaw(); } catch (Throwable ignored) {}
                        boolean isPlaying = false;
                        try { isPlaying = transport.isPlaying().get(); } catch (Throwable ignored) {}
                        boolean isRecording = false;
                        try { isRecording = transport.isArrangerRecordEnabled().get(); } catch (Throwable ignored) {}
                        boolean isOverdub = false;
                        try { isOverdub = transport.isArrangerOverdubEnabled().get(); } catch (Throwable ignored) {}
                        boolean loopEnabled = false;
                        try { loopEnabled = transport.isArrangerLoopEnabled().get(); } catch (Throwable ignored) {}
                        double loopStart = 0.0;
                        try { loopStart = transport.arrangerLoopStart().get(); } catch (Throwable ignored) {}
                        double loopDuration = 16.0;
                        try { loopDuration = transport.arrangerLoopDuration().get(); } catch (Throwable ignored) {}

                        Map<String, Object> timeline = new LinkedHashMap<>();
                        timeline.put("position_beats", playPosition);
                        timeline.put("tempo", tempo);
                        timeline.put("is_playing", isPlaying);
                        timeline.put("is_recording", isRecording);
                        timeline.put("is_overdub", isOverdub);
                        timeline.put("loop_enabled", loopEnabled);
                        timeline.put("loop_start_beat", loopStart);
                        timeline.put("loop_duration_beats", loopDuration);

                        if (arranger != null) {
                            try { timeline.put("playback_follow", arranger.isPlaybackFollowEnabled().get()); } catch (Throwable ignored) {}
                            try { timeline.put("timeline_visible", arranger.isTimelineVisible().get()); } catch (Throwable ignored) {}
                            try { timeline.put("clip_launcher_visible", arranger.isClipLauncherVisible().get()); } catch (Throwable ignored) {}
                            try { timeline.put("cue_markers_visible", arranger.areCueMarkersVisible().get()); } catch (Throwable ignored) {}
                        }
                        res.put("timeline", timeline);

                        // Cue markers (structure / arrangement sections)
                        List<Map<String, Object>> markersList = new ArrayList<>();
                        if (cueBank != null) {
                            int count = cueBank.getSizeOfBank();
                            for (int m = 0; m < count; m++) {
                                CueMarker marker = (CueMarker) cueBank.getItemAt(m);
                                boolean exists = false;
                                try { exists = marker.exists().get(); } catch (Throwable ignored) {}
                                if (!exists) continue;

                                Map<String, Object> mInfo = new LinkedHashMap<>();
                                mInfo.put("index", m);
                                String name = "";
                                try { name = marker.getName().get(); } catch (Throwable ignored) {}
                                mInfo.put("name", name);
                                double pos = 0.0;
                                try { pos = marker.position().get(); } catch (Throwable ignored) {}
                                mInfo.put("position_beat", pos);
                                mInfo.put("bar", (int) Math.floor(pos / 4.0) + 1);

                                try {
                                    Color c = marker.getColor().get();
                                    if (c != null) {
                                        mInfo.put("color", c.toHex());
                                    }
                                } catch (Throwable ignored) {}

                                markersList.add(mInfo);
                            }
                        }
                        res.put("cue_markers", markersList);
                        res.put("cue_markers_count", markersList.size());

                        // Selected arranger clip cursor inspection
                        Clip arrClip = extension.getArrangerCursorClip();
                        boolean clipExists = false;
                        if (arrClip != null) {
                            try { clipExists = arrClip.exists().get(); } catch (Throwable ignored) {}
                        }

                        if (!clipExists || arrClip == null) {
                            res.put("selected_clip", null);
                            future.complete(res);
                            return;
                        }

                        double clipPlayStart = 0.0;
                        try { clipPlayStart = arrClip.getPlayStart().get(); } catch (Throwable ignored) {}
                        double clipPlayStop = 16.0;
                        try { clipPlayStop = arrClip.getPlayStop().get(); } catch (Throwable ignored) {}
                        boolean clipLoopEnabled = true;
                        try { clipLoopEnabled = arrClip.isLoopEnabled().get(); } catch (Throwable ignored) {}
                        double clipLoopStart = 0.0;
                        try { clipLoopStart = arrClip.getLoopStart().get(); } catch (Throwable ignored) {}
                        double clipLoopLength = 16.0;
                        try { clipLoopLength = arrClip.getLoopLength().get(); } catch (Throwable ignored) {}
                        int playingStep = -1;
                        try { playingStep = arrClip.playingStep().get(); } catch (Throwable ignored) {}

                        // Identify track of arranger clip if available
                        String trackName = "";
                        int trackIdx = -1;
                        try {
                            Track t = arrClip.getTrack();
                            if (t != null && t.exists().get()) {
                                trackName = t.name().get();
                                trackIdx = t.position().get();
                            }
                        } catch (Throwable ignored) {}

                        Map<String, Map<String, Object>> noteMap = new LinkedHashMap<>();

                        // 1. Observer snapshots
                        for (BitwigAgentExtension.StepSnapshot snap : extension.getArrangerClipSteps().values()) {
                            if (snap.state == 1) {
                                String k = snap.x + ":" + snap.y;
                                Map<String, Object> noteObj = new LinkedHashMap<>();
                                noteObj.put("step", snap.x);
                                noteObj.put("beat", snap.x * 0.25);
                                noteObj.put("pitch", snap.y);
                                noteObj.put("name", pitchToName(snap.y));
                                noteObj.put("velocity", (int) Math.round(snap.velocity * 127.0));
                                noteObj.put("duration", snap.duration);
                                noteObj.put("channel", snap.channel);
                                noteMap.put(k, noteObj);
                            }
                        }

                        // 2. Direct scan up to active length
                        double scanBeats = Math.max(clipLoopLength, clipPlayStop);
                        int maxScanStep = Math.min(BitwigAgentExtension.GRID_STEPS, Math.max(64, (int) Math.ceil(scanBeats * 4.0)));
                        for (int x = 0; x < maxScanStep; x++) {
                            for (int y = 0; y < 128; y++) {
                                NoteStep ns = arrClip.getStep(0, x, y);
                                if (ns != null && ns.state() != null && "NoteOn".equals(ns.state().name())) {
                                    String k = x + ":" + y;
                                    if (!noteMap.containsKey(k)) {
                                        Map<String, Object> noteObj = new LinkedHashMap<>();
                                        noteObj.put("step", x);
                                        noteObj.put("beat", x * 0.25);
                                        noteObj.put("pitch", y);
                                        noteObj.put("name", pitchToName(y));
                                        noteObj.put("velocity", (int) Math.round(ns.velocity() * 127.0));
                                        noteObj.put("duration", ns.duration());
                                        noteObj.put("channel", ns.channel());
                                        noteMap.put(k, noteObj);
                                    }
                                }
                            }
                        }

                        List<Map<String, Object>> notesList = new ArrayList<>(noteMap.values());
                        notesList.sort((a, b) -> {
                            int sa = ((Number) a.get("step")).intValue();
                            int sb = ((Number) b.get("step")).intValue();
                            if (sa != sb) return Integer.compare(sa, sb);
                            int pa = ((Number) a.get("pitch")).intValue();
                            int pb = ((Number) b.get("pitch")).intValue();
                            return Integer.compare(pa, pb);
                        });

                        Map<String, Object> clipInfo = new LinkedHashMap<>();
                        clipInfo.put("has_content", true);
                        if (trackIdx >= 0) clipInfo.put("track", trackIdx);
                        if (!trackName.isEmpty()) clipInfo.put("track_name", trackName);
                        clipInfo.put("play_start", clipPlayStart);
                        clipInfo.put("play_stop", clipPlayStop);
                        clipInfo.put("loop_enabled", clipLoopEnabled);
                        clipInfo.put("loop_start", clipLoopStart);
                        clipInfo.put("loop_length", clipLoopLength > 0 ? clipLoopLength : 16.0);
                        clipInfo.put("playing_step", playingStep);
                        clipInfo.put("notes", notesList);
                        clipInfo.put("notes_count", notesList.size());

                        res.put("selected_clip", clipInfo);
                        future.complete(res);

                    } catch (Throwable t) {
                        future.completeExceptionally(t);
                    }
                }, 0);

                Map<String, Object> res = future.get(5, TimeUnit.SECONDS);
                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private int resolveTrackIndex(Object param) {
        if (param == null) return -1;
        TrackBank bank = extension.getTrackBank();
        int size = bank.getSizeOfBank();
        if (param instanceof Number) {
            int idx = ((Number) param).intValue();
            if (idx >= 0 && idx < size) return idx;
            return -1;
        }
        String str = param.toString().trim();
        try {
            int idx = Integer.parseInt(str);
            if (idx >= 0 && idx < size) return idx;
        } catch (NumberFormatException ignored) {}

        for (int i = 0; i < size; i++) {
            Track t = (Track) bank.getItemAt(i);
            if (t.exists().get() && t.name().get().equalsIgnoreCase(str)) {
                return i;
            }
        }
        for (int i = 0; i < size; i++) {
            Track t = (Track) bank.getItemAt(i);
            if (t.exists().get() && t.name().get().toLowerCase().contains(str.toLowerCase())) {
                return i;
            }
        }
        return -1;
    }

    private Action resolveAction(String... candidateIds) {
        Application app = extension.getApplication();
        for (String id : candidateIds) {
            try {
                Action a = app.getAction(id);
                if (a != null) return a;
            } catch (Throwable ignored) {}
        }
        try {
            Action[] actions = app.getActions();
            if (actions != null) {
                for (Action a : actions) {
                    for (String id : candidateIds) {
                        if (id.equalsIgnoreCase(a.getId()) || id.equalsIgnoreCase(a.getName())) {
                            return a;
                        }
                    }
                }
            }
        } catch (Throwable ignored) {}
        return null;
    }

    @SuppressWarnings("unchecked")
    private class TrackMoveHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Object tracksObj = params.get("tracks");
                if (tracksObj == null) {
                    tracksObj = params.get("track");
                }
                List<Object> trackParams = new ArrayList<>();
                if (tracksObj instanceof List) {
                    trackParams.addAll((List<Object>) tracksObj);
                } else if (tracksObj != null) {
                    trackParams.add(tracksObj);
                }

                Object targetParam = params.get("target");
                String posParam = params.containsKey("position") ? String.valueOf(params.get("position")).toLowerCase().trim() : "after";

                final String position = posParam;
                Map<String, Object> res = runOnBitwigThread(() -> {
                    TrackBank bank = extension.getTrackBank();
                    int size = bank.getSizeOfBank();

                    List<Track> sourceTracks = new ArrayList<>();
                    List<String> movedNames = new ArrayList<>();
                    for (Object p : trackParams) {
                        int idx = resolveTrackIndex(p);
                        if (idx >= 0) {
                            Track t = (Track) bank.getItemAt(idx);
                            if (t.exists().get() && !sourceTracks.contains(t)) {
                                sourceTracks.add(t);
                                movedNames.add(t.name().get());
                            }
                        }
                    }

                    if (sourceTracks.isEmpty()) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "No valid source tracks found to move from: " + trackParams);
                        return err;
                    }

                    Track targetTrack = null;
                    String finalPos = position;
                    if ("start".equals(finalPos) || "first".equals(finalPos) || "top".equals(finalPos)) {
                        for (int i = 0; i < size; i++) {
                            Track t = (Track) bank.getItemAt(i);
                            if (t.exists().get()) {
                                targetTrack = t;
                                finalPos = "before";
                                break;
                            }
                        }
                    } else if ("end".equals(finalPos) || "last".equals(finalPos) || "bottom".equals(finalPos)) {
                        for (int i = size - 1; i >= 0; i--) {
                            Track t = (Track) bank.getItemAt(i);
                            if (t.exists().get()) {
                                targetTrack = t;
                                finalPos = "after";
                                break;
                            }
                        }
                    } else if (targetParam != null) {
                        int targetIdx = resolveTrackIndex(targetParam);
                        if (targetIdx >= 0) {
                            targetTrack = (Track) bank.getItemAt(targetIdx);
                        }
                    }

                    if (targetTrack == null) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Target track not found: " + targetParam);
                        return err;
                    }

                    InsertionPoint insertionPoint;
                    if ("before".equals(finalPos)) {
                        insertionPoint = targetTrack.beforeTrackInsertionPoint();
                    } else {
                        insertionPoint = targetTrack.afterTrackInsertionPoint();
                    }

                    Track[] tracksArray = sourceTracks.toArray(new Track[0]);
                    insertionPoint.moveTracks(tracksArray);

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "tracks_moved");
                    r.put("moved_tracks", movedNames);
                    r.put("target_track", targetTrack.name().get());
                    r.put("position", finalPos);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    @SuppressWarnings("unchecked")
    private class TrackGroupHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Object tracksObj = params.get("tracks");
                if (tracksObj == null) tracksObj = params.get("track");
                List<Object> trackParams = new ArrayList<>();
                if (tracksObj instanceof List) {
                    trackParams.addAll((List<Object>) tracksObj);
                } else if (tracksObj != null) {
                    trackParams.add(tracksObj);
                }

                String groupName = (String) params.get("name");
                Object existingGroupParam = params.get("group");

                CompletableFuture<Map<String, Object>> future = new CompletableFuture<>();

                host.scheduleTask(() -> {
                    try {
                        TrackBank bank = extension.getTrackBank();

                        // Case 1: Move tracks into an existing group
                        if (existingGroupParam != null) {
                            int groupIdx = resolveTrackIndex(existingGroupParam);
                            if (groupIdx < 0) {
                                Map<String, Object> err = new LinkedHashMap<>();
                                err.put("error", "Existing group track not found: " + existingGroupParam);
                                future.complete(err);
                                return;
                            }
                            Track groupTrack = (Track) bank.getItemAt(groupIdx);
                            List<Track> toMove = new ArrayList<>();
                            List<String> names = new ArrayList<>();
                            for (Object p : trackParams) {
                                int idx = resolveTrackIndex(p);
                                if (idx >= 0 && idx != groupIdx) {
                                    Track t = (Track) bank.getItemAt(idx);
                                    if (t.exists().get() && !toMove.contains(t)) {
                                        toMove.add(t);
                                        names.add(t.name().get());
                                    }
                                }
                            }
                            if (!toMove.isEmpty()) {
                                groupTrack.afterTrackInsertionPoint().moveTracks(toMove.toArray(new Track[0]));
                            }
                            Map<String, Object> r = new LinkedHashMap<>();
                            r.put("status", "tracks_moved_into_group");
                            r.put("group", groupTrack.name().get());
                            r.put("moved_tracks", names);
                            future.complete(r);
                            return;
                        }

                        // Case 2: Create a new group track
                        List<Track> toGroup = new ArrayList<>();
                        List<String> groupedNames = new ArrayList<>();
                        for (Object p : trackParams) {
                            int idx = resolveTrackIndex(p);
                            if (idx >= 0) {
                                Track t = (Track) bank.getItemAt(idx);
                                if (t.exists().get() && !toGroup.contains(t)) {
                                    toGroup.add(t);
                                    groupedNames.add(t.name().get());
                                }
                            }
                        }

                        if (!toGroup.isEmpty()) {
                            Track first = toGroup.get(0);
                            extension.getCursorTrack().selectChannel(first);
                            first.selectInMixer();
                        }

                        Action groupAction = resolveAction("create_group_track_action", "Group", "create_group_track");
                        if (groupAction != null) {
                            groupAction.invoke();
                        }

                        host.scheduleTask(() -> {
                            try {
                                CursorTrack cursorTrack = extension.getCursorTrack();
                                try {
                                    cursorTrack.selectParent();
                                } catch (Throwable ignored) {}

                                String effectiveName = cursorTrack.name().get();
                                if (groupName != null && !groupName.trim().isEmpty()) {
                                    cursorTrack.setName(groupName.trim());
                                    effectiveName = groupName.trim();
                                }

                                if (toGroup.size() > 1) {
                                    List<Track> remaining = new ArrayList<>();
                                    for (int i = 1; i < toGroup.size(); i++) {
                                        remaining.add(toGroup.get(i));
                                    }
                                    try {
                                        cursorTrack.afterTrackInsertionPoint().moveTracks(remaining.toArray(new Track[0]));
                                    } catch (Throwable ignored) {}
                                }

                                Map<String, Object> r = new LinkedHashMap<>();
                                r.put("status", "group_created");
                                r.put("group_name", effectiveName);
                                r.put("grouped_tracks", groupedNames);
                                future.complete(r);
                            } catch (Throwable t) {
                                future.completeExceptionally(t);
                            }
                        }, 200);

                    } catch (Throwable t) {
                        future.completeExceptionally(t);
                    }
                }, 0);

                Map<String, Object> res = future.get(5, TimeUnit.SECONDS);
                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TrackUngroupHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Object trackParam = params.get("track");

                Map<String, Object> res = runOnBitwigThread(() -> {
                    int trackIdx = resolveTrackIndex(trackParam);
                    if (trackIdx < 0) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Track not found: " + trackParam);
                        return err;
                    }
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    extension.getCursorTrack().selectChannel(track);
                    track.selectInMixer();

                    Action ungroupAction = resolveAction("Ungroup", "ungroup");
                    if (ungroupAction != null) {
                        ungroupAction.invoke();
                    }

                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "ungrouped");
                    r.put("track", track.name().get());
                    return r;
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TrackRenameHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Object trackParam = params.get("track");
                String name = (String) params.get("name");

                Map<String, Object> res = runOnBitwigThread(() -> {
                    int trackIdx = resolveTrackIndex(trackParam);
                    if (trackIdx < 0) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Track not found: " + trackParam);
                        return err;
                    }
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    if (name != null && !name.trim().isEmpty()) {
                        track.setName(name.trim());
                    }
                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "renamed");
                    r.put("track_index", trackIdx);
                    r.put("name", name != null ? name.trim() : track.name().get());
                    return r;
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class TrackControlHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String body = readBody(exchange);
                Map<String, Object> params = JsonUtils.parseObject(body);
                Object trackParam = params.get("track");
                Object volumeObj = params.get("volume");
                Object panObj = params.get("pan");
                Object muteObj = params.get("mute");
                Object soloObj = params.get("solo");
                Object armObj = params.get("arm");
                String nameObj = (String) params.get("name");

                Map<String, Object> res = runOnBitwigThread(() -> {
                    int trackIdx = resolveTrackIndex(trackParam);
                    if (trackIdx < 0) {
                        Map<String, Object> err = new LinkedHashMap<>();
                        err.put("error", "Track not found: " + trackParam);
                        return err;
                    }
                    Track track = (Track) extension.getTrackBank().getItemAt(trackIdx);
                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("status", "success");
                    r.put("track_index", trackIdx);
                    r.put("track_name", track.name().get());

                    if (volumeObj instanceof Number) {
                        double volVal = ((Number) volumeObj).doubleValue();
                        double normVol;
                        if (volVal < 0.0) {
                            // If passed in negative dB (e.g. -6 dB)
                            double linear = Math.pow(10.0, volVal / 20.0);
                            normVol = Math.min(1.0, Math.max(0.0, linear * 0.8));
                        } else {
                            normVol = Math.min(1.0, Math.max(0.0, volVal));
                        }
                        track.volume().setImmediately(normVol);
                        r.put("volume", normVol);
                    }

                    if (panObj instanceof Number) {
                        double panVal = ((Number) panObj).doubleValue();
                        double normPan;
                        if (panVal >= -1.0 && panVal <= 1.0) {
                            // Bipolar pan: -1.0 is hard Left (0.0), 0.0 is Center (0.5), +1.0 is hard Right (1.0)
                            normPan = (panVal + 1.0) / 2.0;
                        } else {
                            normPan = Math.min(1.0, Math.max(0.0, panVal));
                        }
                        track.pan().setImmediately(normPan);
                        r.put("pan", normPan);
                    }

                    if (muteObj instanceof Boolean) {
                        boolean m = (Boolean) muteObj;
                        track.mute().set(m);
                        r.put("mute", m);
                    } else if ("toggle".equals(muteObj)) {
                        track.mute().toggle();
                        r.put("mute_toggled", true);
                    }

                    if (soloObj instanceof Boolean) {
                        boolean s = (Boolean) soloObj;
                        track.solo().set(s);
                        r.put("solo", s);
                    } else if ("toggle".equals(soloObj)) {
                        track.solo().toggle();
                        r.put("solo_toggled", true);
                    }

                    if (armObj instanceof Boolean) {
                        boolean a = (Boolean) armObj;
                        track.arm().set(a);
                        r.put("arm", a);
                    } else if ("toggle".equals(armObj)) {
                        track.arm().toggle();
                        r.put("arm_toggled", true);
                    }

                    if (nameObj != null && !nameObj.trim().isEmpty()) {
                        track.setName(nameObj.trim());
                        r.put("name", nameObj.trim());
                    }

                    return r;
                }).get(3, TimeUnit.SECONDS);

                int status = res.containsKey("error") ? 400 : 200;
                sendJson(exchange, status, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }

    private class ActionsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                handleCors(exchange);
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            try {
                String q = "";
                String query = exchange.getRequestURI().getQuery();
                if (query != null && query.contains("q=")) {
                    for (String part : query.split("&")) {
                        if (part.startsWith("q=")) {
                            q = java.net.URLDecoder.decode(part.substring(2), StandardCharsets.UTF_8).toLowerCase();
                        }
                    }
                }
                final String filter = q;
                Map<String, Object> res = runOnBitwigThread(() -> {
                    Action[] actions = extension.getApplication().getActions();
                    List<Map<String, String>> list = new ArrayList<>();
                    if (actions != null) {
                        for (Action a : actions) {
                            String id = a.getId();
                            String name = a.getName();
                            String menu = a.getMenuItemText();
                            if (filter.isEmpty() || (id != null && id.toLowerCase().contains(filter))
                                || (name != null && name.toLowerCase().contains(filter))
                                || (menu != null && menu.toLowerCase().contains(filter))) {
                                Map<String, String> item = new LinkedHashMap<>();
                                item.put("id", id);
                                item.put("name", name);
                                item.put("menu", menu);
                                list.add(item);
                            }
                        }
                    }
                    Map<String, Object> r = new LinkedHashMap<>();
                    r.put("count", list.size());
                    r.put("actions", list);
                    return r;
                }).get(3, TimeUnit.SECONDS);

                sendJson(exchange, 200, res);
            } catch (Exception e) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("error", e.getMessage());
                sendJson(exchange, 500, err);
            }
        }
    }
}

