package com.bitwig.agent;

import com.bitwig.extension.controller.api.*;
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
        server.createContext("/api/instrument/add", new InstrumentAddHandler());
        server.createContext("/api/track/inspect", new TrackInspectHandler());
        server.createContext("/api/clip/inspect", new ClipInspectHandler());

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
                    } else {
                        r.put("error", "Unknown transport action: " + action);
                    }
                    r.put("isPlaying", transport.isPlaying().get());
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

    private static final Map<String, UUID> BITWIG_INSTRUMENTS = new LinkedHashMap<>();
    static {
        BITWIG_INSTRUMENTS.put("polymer", UUID.fromString("8f58138b-03aa-4e9d-83bd-a038c99a4ed5"));
        BITWIG_INSTRUMENTS.put("polysynth", UUID.fromString("a9ffacb5-33e9-4fc7-8621-b1af31e410ef"));
        BITWIG_INSTRUMENTS.put("fm-4", UUID.fromString("7a0a94df-3aa4-4bb5-8e24-2511999871ad"));
        BITWIG_INSTRUMENTS.put("fm4", UUID.fromString("7a0a94df-3aa4-4bb5-8e24-2511999871ad"));
        BITWIG_INSTRUMENTS.put("phase-4", UUID.fromString("252723bf-68a6-4ee6-81f8-95ba4d0fb467"));
        BITWIG_INSTRUMENTS.put("phase4", UUID.fromString("252723bf-68a6-4ee6-81f8-95ba4d0fb467"));
        BITWIG_INSTRUMENTS.put("sampler", UUID.fromString("468bc14b-b2e7-45a1-9666-e83117fe404e"));
        BITWIG_INSTRUMENTS.put("drum_machine", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_INSTRUMENTS.put("drummachine", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_INSTRUMENTS.put("drums", UUID.fromString("8ea97e45-0255-40fd-bc7e-94419741e9d1"));
        BITWIG_INSTRUMENTS.put("organ", UUID.fromString("f2dcfe9a-7b66-4c84-984a-b25685a1c21a"));
        BITWIG_INSTRUMENTS.put("poly_grid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_INSTRUMENTS.put("polygrid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_INSTRUMENTS.put("the_grid", UUID.fromString("a33bba66-8cd4-4f89-aee5-68bf67f70a54"));
        BITWIG_INSTRUMENTS.put("instrument_layer", UUID.fromString("5024be2e-65d6-4d40-bbfe-8b2ea993c445"));
    }

    private static UUID resolveInstrumentUuid(String nameOrUuid) {
        if (nameOrUuid == null || nameOrUuid.trim().isEmpty()) {
            return null;
        }
        String key = nameOrUuid.trim().toLowerCase(Locale.ROOT);
        if (BITWIG_INSTRUMENTS.containsKey(key)) {
            return BITWIG_INSTRUMENTS.get(key);
        }
        try {
            return UUID.fromString(nameOrUuid.trim());
        } catch (IllegalArgumentException e) {
            return null;
        }
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
}
