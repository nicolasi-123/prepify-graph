import React from 'react';
import cytoscape from 'cytoscape';
import svg from 'cytoscape-svg';
import jsPDF from 'jspdf';
import { saveAs } from 'file-saver';

cytoscape.use(svg);

function ExportControls({ cyRef, pathData }) {
  const exportAsPDF = async () => {
    if (!cyRef.current) return;

    try {
      // Use Cytoscape's native PNG (much sharper than html2canvas)
      const pngData = cyRef.current.png({ scale: 4, full: true, bg: '#ffffff' });

      const img = new Image();
      img.onload = () => {
        const pdf = new jsPDF({
          orientation: img.width > img.height ? 'l' : 'p',
          unit: 'mm',
          format: 'a4'
        });

        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();
        const margin = 10;
        const availW = pdfWidth - margin * 2;
        const availH = pdfHeight - margin * 2 - 12; // reserve space for footer

        // Fit image proportionally
        const ratio = Math.min(availW / img.width, availH / img.height);
        const imgW = img.width * ratio;
        const imgH = img.height * ratio;
        const x = margin + (availW - imgW) / 2;
        const y = margin + (availH - imgH) / 2;

        pdf.addImage(pngData, 'PNG', x, y, imgW, imgH);

        // Footer text
        pdf.setFontSize(9);
        pdf.setTextColor(120);
        pdf.text('Prepify Graph - Relationship Visualization', margin, pdfHeight - 8);
        pdf.text(`Generated: ${new Date().toLocaleString()}`, margin, pdfHeight - 4);

        pdf.save('prepify-graph.pdf');
      };
      img.src = pngData;
    } catch (error) {
      console.error('PDF export error:', error);
      alert('Error exporting PDF');
    }
  };

  const exportAsSVG = () => {
    if (!cyRef.current) return;

    try {
      const svgContent = cyRef.current.svg({ scale: 2, full: true, bg: '#ffffff' });
      const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
      saveAs(blob, 'prepify-graph.svg');
    } catch (error) {
      console.error('SVG export error:', error);
      alert('Error exporting SVG. Try PNG instead.');
    }
  };

  const exportAsJSON = () => {
    if (!pathData) {
      alert('No path data to export');
      return;
    }

    try {
      const exportData = {
        exported_at: new Date().toISOString(),
        paths: pathData.paths,
        graph_stats: {
          total_paths: pathData.count,
          source: pathData.paths[0]?.details[0]?.name || 'Unknown',
          target: pathData.paths[0]?.details[pathData.paths[0].details.length - 1]?.name || 'Unknown'
        }
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      });
      saveAs(blob, 'prepify-graph-data.json');
    } catch (error) {
      console.error('JSON export error:', error);
      alert('Error exporting JSON');
    }
  };

  const exportAsPNG = async () => {
    if (!cyRef.current) return;

    try {
      const png = cyRef.current.png({
        scale: 3,
        full: true,
        bg: '#ffffff'
      });

      const response = await fetch(png);
      const blob = await response.blob();
      saveAs(blob, 'prepify-graph.png');
    } catch (error) {
      console.error('PNG export error:', error);
      alert('Error exporting PNG');
    }
  };

  return (
    <div className="export-controls">
      <h3>Export Options</h3>
      <div className="export-buttons">
        <button onClick={exportAsPDF} className="export-btn pdf-btn">
          Export as PDF
        </button>
        <button onClick={exportAsSVG} className="export-btn svg-btn">
          Export as SVG
        </button>
        <button onClick={exportAsPNG} className="export-btn png-btn">
          Export as PNG
        </button>
        <button onClick={exportAsJSON} className="export-btn json-btn">
          Export Data (JSON)
        </button>
      </div>
    </div>
  );
}

export default ExportControls;
