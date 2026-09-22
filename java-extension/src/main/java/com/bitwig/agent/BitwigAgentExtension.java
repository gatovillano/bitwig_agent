package com.bitwig.agent;

import com.bitwig.extension.controller.ControllerExtension;
import com.bitwig.extension.controller.api.*;

/**
 * ControllerExtension implementation for Bitwig Studio.
 * Exposes Bitwig's internals to the local BridgeHttpServer.
 */
public class BitwigAgentExtension extends ControllerExtension {

    private final ControllerHost host;
    private Transport transport;
    private TrackBank trackBank;
    private DeviceBank[] trackDeviceBanks;
    private CursorRemoteControlsPage[][] trackRemotePages;
    private CursorTrack cursorTrack;
    private PinnableCursorClip cursorClip;
    private Application application;
    private Arranger arranger;
    private CueMarkerBank cueMarkerBank;
    private Clip arrangerCursorClip;
    private BridgeHttpServer httpServer;

    public static final int GRID_STEPS = 1024;
    public static final int CUE_MARKERS_CAPACITY = 32;

    protected BitwigAgentExtension(BitwigAgentExtensionDefinition definition, ControllerHost host) {
        super(definition, host);
        this.host = host;
    }

    @Override
    public void init() {
        application = host.createApplication();
        transport = host.createTransport();
        transport.isPlaying().markInterested();
        transport.tempo().value().markInterested();
        transport.isArrangerRecordEnabled().markInterested();
        transport.isArrangerOverdubEnabled().markInterested();
        transport.isArrangerLoopEnabled().markInterested();
        transport.arrangerLoopStart().markInterested();
        transport.arrangerLoopDuration().markInterested();
        transport.getPosition().markInterested();

        arranger = host.createArranger();
        arranger.isPlaybackFollowEnabled().markInterested();
        arranger.isTimelineVisible().markInterested();
        arranger.isClipLauncherVisible().markInterested();
        arranger.areCueMarkersVisible().markInterested();

        cueMarkerBank = arranger.createCueMarkerBank(CUE_MARKERS_CAPACITY);
        for (int m = 0; m < CUE_MARKERS_CAPACITY; m++) {
            CueMarker marker = (CueMarker) cueMarkerBank.getItemAt(m);
            marker.exists().markInterested();
            marker.getName().markInterested();
            marker.position().markInterested();
            marker.getColor().markInterested();
        }

        arrangerCursorClip = host.createArrangerCursorClip(GRID_STEPS, 128);
        arrangerCursorClip.exists().markInterested();
        arrangerCursorClip.setStepSize(0.25);
        arrangerCursorClip.scrollToStep(0);
        arrangerCursorClip.getPlayStart().markInterested();
        arrangerCursorClip.getPlayStop().markInterested();
        arrangerCursorClip.isLoopEnabled().markInterested();
        arrangerCursorClip.getLoopStart().markInterested();
        arrangerCursorClip.getLoopLength().markInterested();
        arrangerCursorClip.getShuffle().markInterested();
        arrangerCursorClip.getAccent().markInterested();
        arrangerCursorClip.playingStep().markInterested();

        arrangerCursorClip.addNoteStepObserver(noteStep -> {
            String key = noteStep.channel() + ":" + noteStep.x() + ":" + noteStep.y();
            String stateName = noteStep.state() != null ? noteStep.state().name() : "";
            if ("NoteOn".equals(stateName) || "NoteSustain".equals(stateName)) {
                arrangerClipSteps.put(key, new StepSnapshot(
                    noteStep.channel(),
                    noteStep.x(),
                    noteStep.y(),
                    "NoteOn".equals(stateName) ? 1 : 2,
                    noteStep.velocity(),
                    noteStep.duration()
                ));
            } else {
                arrangerClipSteps.remove(key);
            }
        });

        // Create a 32-track bank with 2 sends and 16 scene slots per track
        trackBank = host.createTrackBank(32, 2, 16);
        trackDeviceBanks = new DeviceBank[32];
        trackRemotePages = new CursorRemoteControlsPage[32][16];
        for (int i = 0; i < 32; i++) {
            Track t = (Track) trackBank.getItemAt(i);
            t.name().markInterested();
            t.trackType().markInterested();
            t.volume().displayedValue().markInterested();
            t.pan().displayedValue().markInterested();
            t.isGroup().markInterested();
            t.arm().markInterested();
            t.mute().markInterested();
            t.solo().markInterested();
            t.exists().markInterested();

            ClipLauncherSlotBank slotBank = t.clipLauncherSlotBank();
            for (int s = 0; s < 16; s++) {
                ClipLauncherSlot slot = (ClipLauncherSlot) slotBank.getItemAt(s);
                slot.hasContent().markInterested();
                slot.isPlaying().markInterested();
                slot.isSelected().markInterested();
                slot.isRecording().markInterested();
                slot.isPlaybackQueued().markInterested();
                slot.name().markInterested();
            }

            DeviceBank devBank = t.createDeviceBank(16);
            trackDeviceBanks[i] = devBank;
            for (int d = 0; d < 16; d++) {
                Device dev = devBank.getDevice(d);
                dev.exists().markInterested();
                dev.name().markInterested();
                dev.isEnabled().markInterested();
                dev.isPlugin().markInterested();
                dev.deviceType().markInterested();
                dev.presetName().markInterested();
                dev.presetCategory().markInterested();

                CursorRemoteControlsPage remotes = dev.createCursorRemoteControlsPage(8);
                trackRemotePages[i][d] = remotes;
                remotes.pageNames().markInterested();
                remotes.pageCount().markInterested();
                remotes.selectedPageIndex().markInterested();
                remotes.getName().markInterested();
                for (int p = 0; p < 8; p++) {
                    RemoteControl rc = remotes.getParameter(p);
                    rc.name().markInterested();
                    rc.value().markInterested();
                    rc.displayedValue().markInterested();
                }
            }
        }

        cursorTrack = host.createCursorTrack("BITWIG_AGENT_TRACK", "Agent Track", 2, 16, true);
        cursorTrack.name().markInterested();

        // 1024 steps (64 bars of 16th notes / 256 beats), 128 keys (all MIDI pitches 0-127)
        cursorClip = cursorTrack.createLauncherCursorClip("BITWIG_AGENT_CLIP", "Agent Clip", GRID_STEPS, 128);
        cursorClip.exists().markInterested();
        cursorClip.setStepSize(0.25); // 16th notes per step (0.25 beats)
        cursorClip.scrollToStep(0);
        cursorClip.getPlayStart().markInterested();
        cursorClip.getPlayStop().markInterested();
        cursorClip.isLoopEnabled().markInterested();
        cursorClip.getLoopStart().markInterested();
        cursorClip.getLoopLength().markInterested();
        cursorClip.getShuffle().markInterested();
        cursorClip.getAccent().markInterested();
        cursorClip.playingStep().markInterested();

        cursorClip.addNoteStepObserver(noteStep -> {
            String key = noteStep.channel() + ":" + noteStep.x() + ":" + noteStep.y();
            String stateName = noteStep.state() != null ? noteStep.state().name() : "";
            if ("NoteOn".equals(stateName) || "NoteSustain".equals(stateName)) {
                currentClipSteps.put(key, new StepSnapshot(
                    noteStep.channel(),
                    noteStep.x(),
                    noteStep.y(),
                    "NoteOn".equals(stateName) ? 1 : 2,
                    noteStep.velocity(),
                    noteStep.duration()
                ));
            } else {
                currentClipSteps.remove(key);
            }
        });

        try {
            httpServer = new BridgeHttpServer(this, host, 8989);
            httpServer.start();
        } catch (Exception e) {
            host.errorln("[BitwigAgent] Failed to start HTTP server: " + e.getMessage());
        }

        host.showPopupNotification("Bitwig Agent Bridge Active (port 8989)");
        host.println("[BitwigAgent] Bridge initialized successfully on port 8989.");
    }

    @Override
    public void exit() {
        if (httpServer != null) {
            httpServer.stop();
        }
        host.println("[BitwigAgent] Bridge extension stopped.");
    }

    @Override
    public void flush() {
    }

    public int getApiVersion() {
        return getExtensionDefinition().getRequiredAPIVersion();
    }

    public Transport getTransport() {
        return transport;
    }

    public TrackBank getTrackBank() {
        return trackBank;
    }

    public CursorTrack getCursorTrack() {
        return cursorTrack;
    }

    public PinnableCursorClip getCursorClip() {
        return cursorClip;
    }

    public Application getApplication() {
        return application;
    }

    public DeviceBank getDeviceBank(int trackIndex) {
        if (trackDeviceBanks != null && trackIndex >= 0 && trackIndex < trackDeviceBanks.length) {
            return trackDeviceBanks[trackIndex];
        }
        return null;
    }

    public CursorRemoteControlsPage getRemoteControlsPage(int trackIndex, int deviceIndex) {
        if (trackRemotePages != null && trackIndex >= 0 && trackIndex < trackRemotePages.length) {
            if (deviceIndex >= 0 && deviceIndex < trackRemotePages[trackIndex].length) {
                return trackRemotePages[trackIndex][deviceIndex];
            }
        }
        return null;
    }

    public Arranger getArranger() {
        return arranger;
    }

    public CueMarkerBank getCueMarkerBank() {
        return cueMarkerBank;
    }

    public Clip getArrangerCursorClip() {
        return arrangerCursorClip;
    }

    public static class StepSnapshot {
        public final int channel;
        public final int x;
        public final int y;
        public final int state; // 1 = NoteOn, 2 = NoteSustain, 0 = Empty
        public final double velocity;
        public final double duration;

        public StepSnapshot(int channel, int x, int y, int state, double velocity, double duration) {
            this.channel = channel;
            this.x = x;
            this.y = y;
            this.state = state;
            this.velocity = velocity;
            this.duration = duration;
        }
    }

    private final java.util.Map<String, StepSnapshot> currentClipSteps = new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.Map<String, StepSnapshot> arrangerClipSteps = new java.util.concurrent.ConcurrentHashMap<>();

    public java.util.Map<String, StepSnapshot> getCurrentClipSteps() {
        return currentClipSteps;
    }

    public void clearCurrentClipSteps() {
        currentClipSteps.clear();
    }

    public java.util.Map<String, StepSnapshot> getArrangerClipSteps() {
        return arrangerClipSteps;
    }

    public void clearArrangerClipSteps() {
        arrangerClipSteps.clear();
    }
}
