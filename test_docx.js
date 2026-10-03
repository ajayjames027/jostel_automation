const fs = require('fs');
const docx = require('docx');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, WidthType, BorderStyle } = docx;

async function testDocx() {
    try {
        const children = [];
        
        children.push(
            new Paragraph({
                text: "Component 1 – QUIZ Template",
                heading: HeadingLevel.HEADING_1,
                alignment: AlignmentType.CENTER,
                spacing: { after: 200 }
            })
        );
        
        const qNumber = 1;
        const level = 'K1';
        
        children.push(
            new Paragraph({
                children: [new TextRun({ text: `Q-01 – K1 (MC)`, bold: true })],
                spacing: { before: 100, after: 100 }
            })
        );

        const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "000000" };
        const tableBorders = {
            top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder,
            insideHorizontal: tableBorder, insideVertical: tableBorder
        };

        const rows = [];
        rows.push(new TableRow({
            children: [
                new TableCell({
                    children: [new Paragraph({text: "Test Question"})],
                    columnSpan: 3, borders: tableBorders
                }),
                new TableCell({
                    children: [new Paragraph({text: "MC"})],
                    borders: tableBorders
                })
            ]
        }));
        
        const table = new Table({
            rows: rows,
            width: { size: 100, type: WidthType.PERCENTAGE },
            borders: tableBorders
        });
        
        children.push(table);

        const doc = new Document({
            sections: [{ properties: {}, children: children }]
        });

        const buffer = await Packer.toBuffer(doc);
        console.log("SUCCESS!");
    } catch (e) {
        console.error("ERROR:");
        console.error(e.message);
        console.error(e.stack);
    }
}

testDocx();
