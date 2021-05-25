//------------------------------------------------------------------------------
// Basic read and write methods 
//------------------------------------------------------------------------------
//task write(input [{{address_width - 1}}:0] address, input [7:0] data);
//    begin
//        // TODO Implement me - Write address byte (MSb = 0, lower bits are address)
//    end
//endtask
//
//task read(input [{{address_width - 1}}:0] address, output [7:0] data);
//    begin
//        // TODO implement me - Write address byte (MSb = 1, lower bits are address)
//    end
//endtask
//------------------------------------------------------------------------------

//------------------------------------------------------------------------------
// Read all bytes task 
//------------------------------------------------------------------------------
task read_all_bytes(input [{{address_width - 1}}:0] start_address, end_address, output [999:0] data);
    logic [7:0] read_byte;
    begin
        data = '0;
        for (i = 0; i <= (end_address - start_address); i = i + 1) begin
            read(start_address + i, read_byte);
            data[8*i +: 8] = read_byte;
        end
    end
endtask
//------------------------------------------------------------------------------

{% for fname, fdict in fields.items() %}
//------------------------------------------------------------------------------
// Field: {{fname}}
//------------------------------------------------------------------------------
{% for rname, rdict in fdict.registers.items() %}
// Register: {{rname}}
task read_FIELD_{{fname}}_REG_{{rname}}(output [999:0] data);
    logic [999:0] rdata;
    begin
        read_all_bytes({{rdict.lsbit_address}}, {{rdict.msbit_address}}, rdata);
        data = {% raw %}{{{% endraw %}{{1000 - rdict.width}}{% raw %}{{% endraw %}1'b0{% raw %}}}{% endraw %}, rdata[{{((rdict.msbit_address - rdict.lsbit_address) * 8) + rdict.msbit_address_bit_position}}:{{rdict.lsbit_address_bit_position}}]};
    end
endtask
{% if rdict.write %}
task write_FIELD_{{fname}}_REG_{{rname}}(input [999:0] data);
    logic [999:0] rdata, wdata;
    begin
        read_all_bytes({{rdict.lsbit_address}}, {{rdict.msbit_address}}, rdata);
        wdata = rdata;
        wdata[{{((rdict.msbit_address - rdict.lsbit_address) * 8) + rdict.msbit_address_bit_position}}:{{rdict.lsbit_address_bit_position}}] = data;
        for (i = 0; i <= {{rdict.msbit_address - rdict.lsbit_address}}; i = i + 1) begin
            write({{rdict.lsbit_address}} + i, wdata[8*i +: 8]);
        end 
    end 
endtask
{% endif %}
{% if not loop.last %}

{% endif %}
{% endfor %}
//------------------------------------------------------------------------------

{% endfor %}
