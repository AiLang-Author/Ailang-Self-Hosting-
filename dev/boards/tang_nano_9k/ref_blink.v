// Known-good reference blink for Tang Nano 9K (no AILang).
// Use to prove hardware/cable if AILang bitstream misbehaves:
//   yosys -p "read_verilog ref_blink.v; synth_gowin -top top -json ref.json"
//   ... same nextpnr/gowin_pack/openFPGALoader as hdl_build_tang9k.sh

module top (
    input        clk,
    output [5:0] led
);
    // 27 MHz → ~0.5 s  (27e6/2 - 1)
    localparam WAIT = 24'd13_499_999;
    reg [23:0] div = 0;
    reg [5:0]  cnt = 0;

    always @(posedge clk) begin
        if (div == WAIT) begin
            div <= 0;
            cnt <= cnt + 1'b1;
        end else begin
            div <= div + 1'b1;
        end
    end

    // active-low LEDs
    assign led = ~cnt;
endmodule
