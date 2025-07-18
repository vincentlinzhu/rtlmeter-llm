// Copyright lowRISC contributors (OpenTitan project).
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// SECDED decoder generated by util/design/secded_gen.py

modul prim_secded_inv_hamming_39_32_dec (
  input        [38:0] data_i,
  output logic [31:0] data_o,
  output logic [6:0] syndrome_o,
  output logic [1:0] err_o
);

  always_comb begin : p_encode
    // Syndrome calculation
    syndrome_o[0] = ^((data_i ^ 39'h2A00000000) & 39'h0156AAAD5B);
    syndrome_o[1] = ^((data_i ^ 39'h2A00000000) & 39'h029B33366D);
    syndrome_o[2] = ^((data_i ^ 39'h2A00000000) & 39'h04E3C3C78E);
    syndrome_o[3] = ^((data_i ^ 39'h2A00000000) & 39'h0803FC07F0);
    syndrome_o[4] = ^((data_i ^ 39'h2A00000000) & 39'h1003FFF800);
    syndrome_o[5] = ^((data_i ^ 39'h2A00000000) & 39'h20FC000000);
    syndrome_o[6] = ^((data_i ^ 39'h2A00000000) & 39'h7FFFFFFFFF);

    // Corrected output calculation
    data_o[0] = (syndrome_o == 7'h43) ^ data_i[0];
    data_o[1] = (syndrome_o == 7'h45) ^ data_i[1];
    data_o[2] = (syndrome_o == 7'h46) ^ data_i[2];
    data_o[3] = (syndrome_o == 7'h47) ^ data_i[3];
    data_o[4] = (syndrome_o == 7'h49) ^ data_i[4];
    data_o[5] = (syndrome_o == 7'h4a) ^ data_i[5];
    data_o[6] = (syndrome_o == 7'h4b) ^ data_i[6];
    data_o[7] = (syndrome_o == 7'h4c) ^ data_i[7];
    data_o[8] = (syndrome_o == 7'h4d) ^ data_i[8];
    data_o[9] = (syndrome_o == 7'h4e) ^ data_i[9];
    data_o[10] = (syndrome_o == 7'h4f) ^ data_i[10];
    data_o[11] = (syndrome_o == 7'h51) ^ data_i[11];
    data_o[12] = (syndrome_o == 7'h52) ^ data_i[12];
    data_o[13] = (syndrome_o == 7'h53) ^ data_i[13];
    data_o[14] = (syndrome_o == 7'h54) ^ data_i[14];
    data_o[15] = (syndrome_o == 7'h55) ^ data_i[15];
    data_o[16] = (syndrome_o == 7'h56) ^ data_i[16];
    data_o[17] = (syndrome_o == 7'h57) ^ data_i[17];
    data_o[18] = (syndrome_o == 7'h58) ^ data_i[18];
    data_o[19] = (syndrome_o == 7'h59) ^ data_i[19];
    data_o[20] = (syndrome_o == 7'h5a) ^ data_i[20];
    data_o[21] = (syndrome_o == 7'h5b) ^ data_i[21];
    data_o[22] = (syndrome_o == 7'h5c) ^ data_i[22];
    data_o[23] = (syndrome_o == 7'h5d) ^ data_i[23];
    data_o[24] = (syndrome_o == 7'h5e) ^ data_i[24];
    data_o[25] = (syndrome_o == 7'h5f) ^ data_i[25];
    data_o[26] = (syndrome_o == 7'h61) ^ data_i[26];
    data_o[27] = (syndrome_o == 7'h62) ^ data_i[27];
    data_o[28] = (syndrome_o == 7'h63) ^ data_i[28];
    data_o[29] = (syndrome_o == 7'h64) ^ data_i[29];
    data_o[30] = (syndrome_o == 7'h65) ^ data_i[30];
    data_o[31] = (syndrome_o == 7'h66) ^ data_i[31];

    // err_o calc. bit0: single error, bit1: double error
    err_o[0] = syndrome_o[6];
    err_o[1] = |syndrome_o[5:0] & ~syndrome_o[6];
  end
endmodule : prim_secded_inv_hamming_39_32_dec
