// Decompile every function of the current program into one C file (arg0 = output path).
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;

public class DecompileAllToFile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String out = getScriptArgs().length > 0 ? getScriptArgs()[0] : "/tmp/decomp.c";
        DecompInterface ifc = new DecompInterface();
        DecompileOptions opt = new DecompileOptions();
        ifc.setOptions(opt);
        ifc.openProgram(currentProgram);
        int n = 0, bad = 0;
        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (monitor.isCancelled()) break;
                DecompileResults r = ifc.decompileFunction(f, 120, monitor);
                w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint() + " size=" + f.getBody().getNumAddresses());
                if (r != null && r.decompileCompleted()) { w.println(r.getDecompiledFunction().getC()); n++; }
                else { w.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage())); bad++; }
            }
        }
        println("decompiled=" + n + " failed=" + bad + " -> " + out);
    }
}
