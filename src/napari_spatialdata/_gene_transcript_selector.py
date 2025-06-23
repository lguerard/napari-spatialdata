import pandas as pd
from napari.layers import Points
from napari.utils.notifications import show_info
from napari_spatialdata._sdata_widgets import get_sdata_from_viewer
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QListWidget, QPushButton
)
from typing import Optional

class GeneTranscriptSelector(QWidget):
    def __init__(
        self,
        sdata=None,
        points_key=None,  # default: None, select first available
        gene_column='gene',
        transcript_id_column=None,
        viewer=None,
    ):
        super().__init__()
        self.sdata = sdata
        self.points_key = points_key
        self.gene_column = gene_column
        self.transcript_id_column = transcript_id_column
        self.viewer = viewer
        self.points_table = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.gene_label = QLabel("Select Gene:")
        self.layout.addWidget(self.gene_label)

        self.gene_selector = QComboBox()
        self.layout.addWidget(self.gene_selector)

        self.transcript_label = QLabel("Transcripts for selected gene:")
        self.layout.addWidget(self.transcript_label)

        self.transcript_list = QListWidget()
        self.layout.addWidget(self.transcript_list)

        # Add a button to add points to viewer
        self.add_points_btn = QPushButton("Add Points Layer to Viewer")
        self.layout.addWidget(self.add_points_btn)
        self.add_points_btn.clicked.connect(self._on_add_points_clicked)

        # Setup data if provided
        if self.sdata is not None:
            self.set_sdata(self.sdata)
        self.gene_selector.currentTextChanged.connect(self.update_transcripts)

    def set_sdata(self, sdata):
        """Set sdata and extract the points table."""
        self.sdata = sdata
        self.points_table = None

        if hasattr(self.sdata, "points") and hasattr(self.sdata.points, "data"):
            available_keys = list(self.sdata.points.data.keys())
            if not available_keys:
                show_info("No points data found in SpatialData object.")
                return

            # Use given points_key if available, else first key
            key = self.points_key if (self.points_key in available_keys) else available_keys[0]
            self.points_key = key

            points_df = self.sdata.points.data[key]
            if hasattr(points_df, "compute"):
                points_df = points_df.compute()
            self.points_table = points_df

        if (
            self.points_table is not None
            and self.gene_column in self.points_table.columns
        ):
            self.populate_genes()
            if self.gene_selector.count() > 0:
                self.update_transcripts(self.gene_selector.currentText())
        else:
            show_info("No gene column found in points table.")

    def set_viewer(self, viewer):
        self.viewer = viewer

    def populate_genes(self):
        unique_genes = sorted(self.points_table[self.gene_column].unique())
        self.gene_selector.clear()
        self.gene_selector.addItems([str(g) for g in unique_genes])

    def update_transcripts(self, gene):
        self.transcript_list.clear()
        if not gene or self.points_table is None:
            return
        subset = self.points_table[self.points_table[self.gene_column] == gene]
        if self.transcript_id_column and self.transcript_id_column in subset.columns:
            transcript_ids = subset[self.transcript_id_column].astype(str)
            self.transcript_list.addItems(transcript_ids.tolist())
        else:
            for idx, row in subset.iterrows():
                self.transcript_list.addItem(str(row.to_dict()))

    def _on_add_points_clicked(self):
        """Add points to the napari viewer as a layer."""
        if self.points_table is None:
            show_info("No points data available.")
            return
        if self.viewer is None:
            show_info("No viewer found.")
            return
        if not all(col in self.points_table.columns for col in ("x", "y", self.gene_column)):
            show_info("Points table lacks required columns (x, y, gene).")
            return

        coords = self.points_table[["x", "y"]].values
        features = self.points_table[[self.gene_column]]
        try:
            self.viewer.add_points(coords, features=features, name=self.points_key)
        except Exception as e:
            show_info(f"Failed to add points: {e}")

def napari_experimental_provide_dock_widget():
    """
    This function is auto-discovered by napari as an entry point.
    It tries to find a SpatialData object from the viewer.
    """
    def widget_factory(viewer):
        sdata = None
        try:
            sdata = get_sdata_from_viewer(viewer)
        except Exception:
            sdata = None
        widget = GeneTranscriptSelector(sdata)
        widget.set_viewer(viewer)
        return widget
    return widget_factory