import React from 'react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { saveAs } from 'file-saver';

function ExportControls({ cyRef, pathData }) {
  const exportAsPDF = async () => {
    if (!cyRef.current) return;

    try {
      // Get the Cytoscape container
      const container = cyRef.current.container();
      
      // Use html2canvas to capture the graph
      const canvas = await html2canvas(container, {
        backgroundColor: '#ffffff',
        scale: 2
      });

      // Create PDF
      const pdf = new jsPDF('l', 'mm', 'a4');
      const imgData = canvas.toDataURL('image/png');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      
      // Add metadata
      pdf.setFontSize(10);
      pdf.text('Prepify Graph - Relationship Visualization', 10, pdfHeight - 10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, 10, pdfHeight - 5);
      
      pdf.save('prepify-graph.pdf');
    } catch (error) {
      console.error('PDF export error:', error);
      alert('Error exporting PDF');
    }
  };

  const exportAsSVG = () => {
    if (!cyRef.current) return;

    try {
      const svg = cyRef.current.svg({ scale: 2, full: true });
      const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
      saveAs(blob, 'prepify-graph.svg');
    } catch (error) {
      console.error('SVG export error:', error);
      alert('Error exporting SVG');
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
      
      // Convert base64 to blob
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
          📄 Export as PDF
        </button>
        <button onClick={exportAsSVG} className="export-btn svg-btn">
          🎨 Export as SVG
        </button>
        <button onClick={exportAsPNG} className="export-btn png-btn">
          🖼️ Export as PNG
        </button>
        <button onClick={exportAsJSON} className="export-btn json-btn">
          📊 Export Data (JSON)
        </button>
      </div>
    </div>
  );
}

export default ExportControls;