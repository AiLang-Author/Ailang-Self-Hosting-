// Tang Nano 9K top — wraps AILang ailang_top
// LEDs active-low on this board → invert so AILang 1 = lit

module top (
    input        clk,
    output [5:0] led
);
    wire [63:0] Board_div;
    wire [63:0] Board_led;

    ailang_top u_ailang (
        .clk(clk),
        .rst(1'b0),
        .Board_div(Board_div),
        .Board_led(Board_led)
    );

    // Active-low LEDs: light when bit is 1 in AILang
    assign led = ~Board_led[5:0];
endmodule
