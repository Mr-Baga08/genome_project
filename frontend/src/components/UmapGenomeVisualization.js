import React, { useEffect, useState } from "react";
import { Scatter } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend } from "chart.js";

// Register necessary components
ChartJS.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend);

const UmapGenomeVisualization = ({ jsonUrl }) => {
  const [file, setFile] = useState(null);
  const [plotData, setPlotData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = (event) => {
    event.preventDefault(); // Prevent default form submission
    if (file) {
      fetchUMAPData(); // Trigger data fetch
    } else {
      alert("Please select a file to upload.");
    }
  };

  const fetchUMAPData = async () => {
    setIsLoading(true);
  
    const formData = new FormData();
    formData.append("file", file);
  
    try {
      const response = await fetch(jsonUrl, {
        method: "POST",
        body: formData,
      });
  
      if (!response.ok) {
        const errorMessage = await response.text();
        throw new Error(`Server Error: ${errorMessage}`);
      }
  
      const responseData = await response.json();
      const data = JSON.parse(responseData.data);
  
      // Calculate centroids for each cluster
      const centroids = {};
      data.forEach(({ UMAP_1, UMAP_2, Cluster_Kmeans }) => {
        if (!centroids[Cluster_Kmeans]) {
          centroids[Cluster_Kmeans] = { x: 0, y: 0, count: 0 };
        }
        centroids[Cluster_Kmeans].x += UMAP_1;
        centroids[Cluster_Kmeans].y += UMAP_2;
        centroids[Cluster_Kmeans].count += 1;
      });
  
      // Finalize centroids
      Object.keys(centroids).forEach((key) => {
        centroids[key].x /= centroids[key].count;
        centroids[key].y /= centroids[key].count;
      });
  
      // Prepare the scatter plot data
      setPlotData({
        labels: data.map((_, i) => `Sample ${i + 1}`),
        datasets: [
          {
            label: "Genome Data UMAP",
            data: data.map(({ UMAP_1, UMAP_2 }) => ({
              x: UMAP_1,
              y: UMAP_2,
            })),
            backgroundColor: data.map(({ Cluster_Kmeans }) =>
              getColorForCluster(Cluster_Kmeans)
            ),
          },
        ],
        centroids, // Pass centroids for rendering labels
      });
    } catch (error) {
      console.error("Error fetching UMAP data:", error);
      alert(`Failed to fetch UMAP data: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Function to return color based on cluster label
  function getColorForCluster(clusterLabel) {
    const defaultColors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"];
    if (clusterLabel === -1) return "#808080"; // Gray for noise
    return defaultColors[clusterLabel % defaultColors.length];
  }
  
  return (
    <div>
      <h4>Upload CSV for UMAP & Grouping</h4>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".csv" onChange={handleFileChange} />
        <button type="submit" disabled={isLoading}>Submit</button>
      </form>

      {isLoading ? (
        <p>Loading UMAP projection...</p>
      ) : plotData ? (
      <Scatter
        data={plotData}
        options={{
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  const { x, y } = context.raw;
                  return `UMAP Coordinates: (${x.toFixed(2)}, ${y.toFixed(2)})`;
                },
              },
            },
            annotation: {
              annotations: Object.entries(plotData?.centroids || {}).map(
                ([cluster, { x, y }]) => ({
                  type: "label",
                  position: { x, y },
                  content: `Cluster ${cluster}`,
                  color: getColorForCluster(cluster),
                  font: { size: 12, weight: "bold" },
                  backgroundColor: "rgba(255, 255, 255, 0.8)",
                })
              ),
            },
          },
          scales: {
            x: {
              title: { display: true, text: "UMAP 1" },
            },
            y: {
              title: { display: true, text: "UMAP 2" },
            },
          },
        }}
      />

      ) : (
        <p>No data available. Upload a CSV file to start.</p>
      )}
    </div>
  );
};

export default UmapGenomeVisualization;