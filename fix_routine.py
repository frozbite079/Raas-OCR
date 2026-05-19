import re

with open("html_pages/routine_test_certificate.html", "r") as f:
    content = f.read()

# Map labels to data-fields
replacements = [
    (r'<td colspan="2" class="input-cell"\s*style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text"\s*class="form-input"></td>',
     r'<td colspan="2" class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Panel No"></td>'),
    
    (r'<td colspan="2" class="input-cell" style="width: 20%; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>',
     r'<td colspan="2" class="input-cell" style="width: 20%; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="S/S Location"></td>'),

    (r'<td class="input-cell"\s*style="width: 35%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>',
     r'<td class="input-cell" style="width: 35%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Certificate No"></td>'),
    
    (r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input"></td>\s*</tr>\s*<tr>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Customer',
     r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Date"></td>\n                </tr>\n                <tr>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Customer'),

    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>S.O.\s*No.</b></td>',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Customer"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>S.O.\n                            No.</b></td>'),

    (r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input"></td>\s*</tr>\s*<tr>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>WO',
     r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="S.O. No"></td>\n                </tr>\n                <tr>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>WO'),

    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>S.L.',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="WO No"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>S.L.'),

    (r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input"></td>\s*</tr>\s*<tr>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Breaker',
     r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="S/L NO"></td>\n                </tr>\n                <tr>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Breaker'),

    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Rated',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Breaker Type"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Rated'),

    (r'<td class="input-cell"\s*style="width: 12%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>\s*<td class="input-cell" style="width: 8%; border-bottom: 1px solid black;">\s*<div style="display: flex; align-items: center; width: 100%; height: 100%; padding-left: 4px;">\s*<b>VI-</b><input type="text" class="form-input" style="padding-left: 2px;">\s*</div>',
     r'<td class="input-cell" style="width: 12%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Rated Normal Current"></td>\n                    <td class="input-cell" style="width: 8%; border-bottom: 1px solid black;">\n                        <div style="display: flex; align-items: center; width: 100%; height: 100%; padding-left: 4px;">\n                            <b>VI-</b><input type="text" class="form-input" style="padding-left: 2px;" data-field="VI">\n                        </div>'),

    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Feeder',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Mechanism Type"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Feeder'),

    (r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input"></td>\s*</tr>\s*<tr>\s*<td style="border-right: 1px solid black; padding: 4px;"><b>STC:</b></td>',
     r'<td colspan="2" class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input" data-field="Feeder Name"></td>\n                </tr>\n                <tr>\n                    <td style="border-right: 1px solid black; padding: 4px;"><b>STC:</b></td>'),

    (r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input">\s*</td>\s*<td style="border-right: 1px solid black; padding: 4px;"><b>Counter Reading & Operation:</b></td>\s*<td colspan="2" class="input-cell"><input type="text" class="form-input"></td>',
     r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input" data-field="STC">\n                    </td>\n                    <td style="border-right: 1px solid black; padding: 4px;"><b>Counter Reading & Operation:</b></td>\n                    <td colspan="2" class="input-cell"><input type="text" class="form-input" data-field="Counter Reading & Operation"></td>'),
]

# Block 2
replacements.extend([
    (r'<td class="input-cell"\s*style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td\s*style="width: 15%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px; text-align: center;">\s*<b>Tripping Coil</b>\s*</td>\s*<td class="input-cell"\s*style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td\s*style="width: 15%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px; text-align: center;">\s*<b>Motor :</b>\s*</td>\s*<td class="input-cell" style="width: 10%; border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>',
     r'<td class="input-cell" style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Closing Coil VDC"></td>\n                    <td style="width: 15%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px; text-align: center;">\n                        <b>Tripping Coil</b>\n                    </td>\n                    <td class="input-cell" style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Tripping Coil VDC"></td>\n                    <td style="width: 15%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px; text-align: center;">\n                        <b>Motor :</b>\n                    </td>\n                    <td class="input-cell" style="width: 10%; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Motor VAC/DC"></td>'),
    
    (r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input">\s*</td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell"><input type="text" class="form-input text-center"></td>',
     r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input" data-field="Auxiliary Resistance">\n                    </td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Closing Coil Ohm"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Tripping Coil Ohm"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell"><input type="text" class="form-input text-center" data-field="Motor Ohm"></td>')
])

# Block 3
replacements.append(
    (r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell"><input type="text" class="form-input text-center"></td>\s*</tr>\s*</table>',
     r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Contact Resistance R-Phase"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Contact Resistance Y-Phase"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Contact Resistance B-Phase"></td>\n                    <td class="input-cell"><input type="text" class="form-input text-center"></td>\n                </tr>\n            </table>')
)

# Block 4
replacements.extend([
    (r'<td class="input-cell"\s*style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell"\s*style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell"\s*style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell" style="width: 5%; border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*</tr>\s*<tr>\s*<td style="border-right: 1px solid black; padding: 4px;"><b>Opening',
     r'<td class="input-cell" style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Closing Time (ms)"></td>\n                    <td class="input-cell" style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell" style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell" style="width: 5%; border-bottom: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                </tr>\n                <tr>\n                    <td style="border-right: 1px solid black; padding: 4px;"><b>Opening'),
    
    (r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td class="input-cell"><input type="text" class="form-input text-center"></td>\s*</tr>\s*</table>',
     r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="Opening Time (ms)"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center"></td>\n                    <td class="input-cell"><input type="text" class="form-input text-center"></td>\n                </tr>\n            </table>')
])

# Block 5 IR Value
replacements.extend([
    (r'<td class="input-cell"\s*style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td\s*style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;">\s*<b>RY</b>\s*</td>\s*<td class="input-cell"\s*style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>R-R</b>\s*</td>\s*<td class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>',
     r'<td class="input-cell" style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="VCB Close Phase to Earth RE"></td>\n                    <td style="width: 10%; border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;">\n                        <b>RY</b>\n                    </td>\n                    <td class="input-cell" style="width: 20%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="IR value Phase to Phase R-Y"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>R-R</b>\n                    </td>\n                    <td class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="VCB Open Top & Bottom Contact R-R"></td>'),
    
    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>YB</b>\s*</td>\s*<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Y-Y</b>\s*</td>\s*<td class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="VCB Close Phase to Earth YE"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>YB</b>\n                    </td>\n                    <td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="IR value Phase to Phase Y-B"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Y-Y</b>\n                    </td>\n                    <td class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="VCB Open Top & Bottom Contact Y-Y"></td>'),

    (r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; padding: 4px;"><b>BR</b></td>\s*<td class="input-cell" style="border-right: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; padding: 4px;"><b>B-B</b></td>\s*<td class="input-cell"><input type="text" class="form-input text-center"></td>',
     r'<td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="VCB Close Phase to Earth BE"></td>\n                    <td style="border-right: 1px solid black; padding: 4px;"><b>BR</b></td>\n                    <td class="input-cell" style="border-right: 1px solid black;"><input type="text" class="form-input text-center" data-field="IR value Phase to Phase B-R"></td>\n                    <td style="border-right: 1px solid black; padding: 4px;"><b>B-B</b></td>\n                    <td class="input-cell"><input type="text" class="form-input text-center" data-field="VCB Open Top & Bottom Contact B-B"></td>')
])

# Block 6 HV Test
replacements.extend([
    (r'<td class="input-cell"\s*style="width: 30%; border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>',
     r'<td class="input-cell" style="width: 30%; border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Open Position Top & Bottom R-R"></td>\n                    <td class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Open Position Top & Bottom Y-Y"></td>'),

    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>\s*</tr>\s*<tr>\s*<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Close Position Phase to Earth RE"></td>\n                    <td class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Close Position Phase to Earth YE"></td>\n                </tr>\n                <tr>\n                    <td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input'),
    
    (r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Phase to\s*Phase</b></td>\s*<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input\s*type="text" class="form-input text-center"></td>\s*<td class="input-cell" style="border-bottom: 1px solid black;"><input type="text"\s*class="form-input text-center"></td>',
     r'<td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Close Position Phase to Earth BE"></td>\n                    <td style="border-right: 1px solid black; border-bottom: 1px solid black; padding: 4px;"><b>Phase to\n                            Phase</b></td>\n                    <td class="input-cell" style="border-right: 1px solid black; border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Close Position Phase to Phase R-R"></td>\n                    <td class="input-cell" style="border-bottom: 1px solid black;"><input type="text" class="form-input text-center" data-field="Close Position Phase to Phase Y-Y"></td>')
])

# Operations
ops = [
    ("Dashpot Operation", "Dashpot Operation"),
    ("Opening Spring Setting", "Opening Spring Setting"),
    ("Closing Spring Setting", "Closing Spring Setting"),
    ("Snatch Gap", "Snatch Gap"),
    ("Mechanical Operation Test", "Mechanical Operation Test"),
    ("Auxiliary Switch Operation", "Auxiliary Switch Operation"),
    ("Trip free operation", "Trip free operation"),
    ("Motor Cut-off switch Operation", "Motor Cut-off switch Operation"),
    ("Physical Check for any wear & tear", "Physical Check for any wear & tear"),
    ("Physical check of epoxy housing", "Physical check of epoxy housing"),
    ("CB On-Off Operation Manually", "CB On-Off Operation Manually"),
]

for op_html, data_field in ops:
    # Need to replace the next input in the row for this operation
    # E.g. <td colspan="2" ...><b>Dashpot Operation:</b></td>
    #      <td ...><input type="text" class="form-input"></td>
    pattern = r'(<b>' + op_html + r'[^<]*</b>(?:.|\n)*?<input\s*type="text" class="form-input")>'
    replacement = r'\1 data-field="' + data_field + '">'
    replacements.append((pattern, replacement))

replacements.append(
    (r'(<b>Electrical Checks:</b>(?:.|\n)*?<input type="text"\s*class="form-input text-center")>',
     r'\1 data-field="Electrical Checks">')
)

replacements.append(
    (r'(<b>CB\s*ON-OFF Operation Electrically:</b>(?:.|\n)*?<input\s*type="text" class="form-input")>',
     r'\1 data-field="CB ON-OFF Operation Electrically">')
)

replacements.append(
    (r'(<b>Spring\s*Charging Motor Operation:</b>(?:.|\n)*?<input\s*type="text" class="form-input")>',
     r'\1 data-field="Spring Charging Motor Operation">')
)

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content, count=1)

with open("html_pages/routine_test_certificate.html", "w") as f:
    f.write(content)

print("Replacement complete")
