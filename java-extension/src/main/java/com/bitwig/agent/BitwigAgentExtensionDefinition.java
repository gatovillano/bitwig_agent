package com.bitwig.agent;

import com.bitwig.extension.api.PlatformType;
import com.bitwig.extension.controller.AutoDetectionMidiPortNamesList;
import com.bitwig.extension.controller.ControllerExtensionDefinition;
import com.bitwig.extension.controller.api.ControllerHost;

import java.util.UUID;

/**
 * Extension definition for the Bitwig Agent Bridge.
 */
public class BitwigAgentExtensionDefinition extends ControllerExtensionDefinition {

    private static final UUID DRIVER_ID = UUID.fromString("b8c19db2-8822-4a0b-967b-40fa18a994ef");

    @Override
    public String getName() {
        return "Bitwig Agent Bridge";
    }

    @Override
    public String getAuthor() {
        return "Bitwig Agent";
    }

    @Override
    public String getVersion() {
        return "1.0.1";
    }

    @Override
    public UUID getId() {
        return DRIVER_ID;
    }

    @Override
    public String getHardwareVendor() {
        return "BitwigAgent";
    }

    @Override
    public String getHardwareModel() {
        return "Agent Bridge";
    }

    @Override
    public int getRequiredAPIVersion() {
        return 18;
    }

    @Override
    public int getNumMidiInPorts() {
        return 0;
    }

    @Override
    public int getNumMidiOutPorts() {
        return 0;
    }

    @Override
    public void listAutoDetectionMidiPortNames(AutoDetectionMidiPortNamesList list, PlatformType platformType) {
    }

    @Override
    public BitwigAgentExtension createInstance(ControllerHost host) {
        return new BitwigAgentExtension(this, host);
    }
}
