// Thin board wrapper for AILang HDL output on Tang Nano 9K (Gowin GW1NR-9).
// Maps ailang_top (clk/rst + FixedPool Board_*) onto physical LED bus.
// LEDs are active-low (common anode) — invert here so AILang counts "lit = 1".

module top (
    input        clk,        // 27 MHz on pin 52
    output [5:0] led         // pins 10,11,13,14,15,16
);
    wire [63:0] Board_div;
    wire [63:0] Board_led;
    wire [63:0] Board_tick;

    // rst tied low: cold start uses FixedPool Initialize / initial blocks
    ailang_top u_ailang (
        .clk(clk),
        .rst(1'b0),
        .Board_div(Board_div),
        .Board_led(Board_led),
        .Board_tick(Board_tick)
    );

    assign led = ~Board_led[5:0];
endmodule
