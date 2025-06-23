import pandas as pd
from napari.layers import Points
from napari.utils.notifications import show_info
from napari_spatialdata._sdata_widgets import get_sdata_from_viewer
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QListWidget
)
from typing import Optional

class GeneTranscriptSelector(QWidget):
    def __init__(
        self,
        sdata=None,
        points_key=None,  # default to None, pick first available
        gene_column='gene',
        transcript_id_column=None,
    ):
        super().__init__()
        self.sdata = sdata
        self.points_key = points_key
        self.gene_column = gene_column
        self.transcript_id_column = transcript_id_column

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

        self.points_table = None
        if self.sdata is not None:
            self.set_sdata(self.sdata)

        self.gene_selector.currentTextChanged.connect(self.update_transcripts)

    def set_sdata(self, sdata):
    self.sdata = sdata
    pt = None
    if hasattr(self.sdata, "points"):
        pt = getattr(self.sdata, "points")
        if hasattr(pt, "data"):
            # pt.data is a dict: keys are point names, values are DataFrames
            if isinstance(pt.data, dict) and len(pt.data) > 0:
                # Use first key by default; could be improved to let user choose
                points_key = list(pt.data.keys())[0]
                self.points_key = points_key
                points_df = pt.data[points_key]
                # Convert Dask DataFrame to pandas if needed
                if hasattr(points_df, "compute"):
                    points_df = points_df.compute()
                self.points_table = points_df
    if self.points_table is not None:
        self.populate_genes()
        if self.gene_selector.count() > 0:
            self.update_transcripts(self.gene_selector.currentText())
    else:
        show_info("No points table found in SpatialData object.")


    def populate_genes(self):
        unique_genes = sorted(self.points_table[self.gene_column].unique())
        self.gene_selector.clear()
        self.gene_selector.addItems(unique_genes)

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

def napari_experimental_provide_dock_widget():
    """
    This function is auto-discovered by napari as an entry point.
    It tries to find a SpatialData object from the viewer.
    """
    def widget_factory(viewer):
        # Try to get the SpatialData object from the viewer using plugin helpers
        sdata = None
        try:
            sdata = get_sdata_from_viewer(viewer)
        except Exception:
            sdata = None
        widget = GeneTranscriptSelector(sdata)
        # Optionally, you could add a button to refresh/reload if needed
        return widget
    return widget_factory