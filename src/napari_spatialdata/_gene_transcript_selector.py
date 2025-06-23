from typing import Any, Dict, List, Optional, Union

import pandas as pd
from napari.layers import Points
from napari.utils.notifications import show_info
from qtpy.QtWidgets import QComboBox, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget


def get_sdata_from_viewer(viewer):
    """
    Retrieve the SpatialData object from napari-spatialdata Interactive mode.

    This function tries multiple methods to find the SpatialData object, including
    checking layer metadata and Interactive mode-specific attributes.

    Parameters
    ----------
    viewer : napari.Viewer
        The napari viewer instance.

    Returns
    -------
    spatialdata.SpatialData or None
        The found SpatialData object or None if not found.

    Examples
    --------
    >>> sdata = get_sdata_from_viewer(viewer)
    >>> if sdata is not None:
    ...     print(f"Found SpatialData with {len(sdata.points)} point tables")
    """

    def log(msg):
        with open("sdata_debug.txt", "a") as f:
            f.write(msg + "\n")

    log("get_sdata_from_viewer called")
    log(f"viewer type: {type(viewer)}")

    # Method 1: Check if the viewer is from napari-spatialdata Interactive
    # Interactive mode typically adds spatialdata_viewer attribute to the viewer
    if hasattr(viewer, "spatialdata_viewer"):
        log("Found spatialdata_viewer attribute")
        if hasattr(viewer.spatialdata_viewer, "sdata"):
            log("Found sdata in spatialdata_viewer")
            return viewer.spatialdata_viewer.sdata

    # Method 2: Look for specific attributes in viewer.window
    if hasattr(viewer, "window"):
        window = viewer.window
        # Check for Interactive mode attributes
        for attr_name in ["_spatialdata", "sdata", "spatialdata"]:
            if hasattr(window, attr_name):
                log(f"Found {attr_name} in viewer.window")
                return getattr(window, attr_name)

    # Method 3: Check for custom data in viewer._sdata or viewer.sdata
    for attr_name in ["_sdata", "sdata", "spatialdata"]:
        if hasattr(viewer, attr_name):
            log(f"Found {attr_name} in viewer")
            return getattr(viewer, attr_name)

    # Method 4: Try to find it in layers metadata (original approach)
    for idx, layer in enumerate(viewer.layers):
        log(f"Layer {idx}: {layer.name}, type={type(layer)}")
        md = getattr(layer, "metadata", {})
        log(f"Layer.metadata: {md}")
        for k, v in md.items():
            log(f"  metadata[{k}]: {type(v)} {v}")
            # Try all plausible keys for SpatialData
            if k.lower() in ("spatialdata_object", "sdata", "spatialdata"):
                log(f"  Found possible SpatialData under key '{k}'")
                return v

    # Method 5: Check for _qt_viewer attribute which might contain sdata
    if hasattr(viewer, "_qt_viewer"):
        qt_viewer = viewer._qt_viewer
        for attr_name in ["sdata", "_sdata", "spatialdata"]:
            if hasattr(qt_viewer, attr_name):
                log(f"Found {attr_name} in viewer._qt_viewer")
                return getattr(qt_viewer, attr_name)

    log("No SpatialData object found in any location")
    return None


class GeneTranscriptSelector(QWidget):
    def __init__(
        self,
        sdata=None,
        points_key=None,  # default: None, select first available
        gene_column="gene",
        transcript_id_column=None,
        viewer=None,
    ):
        """
        Create a widget for selecting genes and transcripts from SpatialData.

        Parameters
        ----------
        sdata : spatialdata.SpatialData, optional
            SpatialData object containing points data with gene information.
        points_key : str, optional
            Key for the specific points table to use. If None, uses first available.
        gene_column : str, default='gene'
            Column name in points table containing gene identifiers.
        transcript_id_column : str, optional
            Column name for transcript identifiers. If None, displays all point info.
        viewer : napari.Viewer, optional
            Napari viewer instance.

        Examples
        --------
        >>> widget = GeneTranscriptSelector(sdata, gene_column='gene_name')
        >>> widget.set_viewer(viewer)
        """
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

        # Add diagnostic button
        self.diagnose_btn = QPushButton("Diagnose Points Issues")
        self.layout.addWidget(self.diagnose_btn)
        self.diagnose_btn.clicked.connect(self.diagnose)

        # Setup data if provided
        if self.sdata is not None:
            self.set_sdata(self.sdata)
        self.gene_selector.currentTextChanged.connect(self.update_transcripts)

    def set_sdata(self, sdata):
        """
        Set SpatialData object and extract points table.

        Parameters
        ----------
        sdata : spatialdata.SpatialData
            SpatialData object containing points data.

        Examples
        --------
        >>> widget.set_sdata(sdata)
        >>> if widget.points_table is not None:
        ...     print(f"Found {len(widget.points_table)} points")
        """

        def log(msg):
            with open("sdata_debug.txt", "a") as f:
                f.write(msg + "\n")

        self.sdata = sdata
        self.points_table = None

        log("set_sdata called")
        log(f"sdata: {repr(self.sdata)}")

        if self.sdata is None:
            log("sdata is None, aborting")
            return

        # Check if points attribute exists
        if not hasattr(self.sdata, "points"):
            log("sdata has no 'points' attribute")
            show_info("SpatialData object has no 'points' attribute.")
            return

        log(f"sdata.points: {repr(self.sdata.points)}")

        # Handle different structures of spatialdata
        points_keys = []

        # Method 1: Direct dictionary-like interface
        if hasattr(self.sdata.points, "keys"):
            points_keys = list(self.sdata.points.keys())
            log(f"Found points keys via direct access: {points_keys}")

            if not points_keys:
                log("No points keys found")
                show_info("No points data found in SpatialData object.")
                return

            # Use given points_key if available, else first key
            key = self.points_key if (self.points_key in points_keys) else points_keys[0]
            self.points_key = key
            log(f"Using points key: {key}")

            points_df = self.sdata.points[key]

        # Method 2: Nested data attribute (older versions)
        elif hasattr(self.sdata.points, "data") and hasattr(self.sdata.points.data, "keys"):
            points_keys = list(self.sdata.points.data.keys())
            log(f"Found points keys via data attribute: {points_keys}")

            if not points_keys:
                log("No points keys found in data")
                show_info("No points data found in SpatialData object.")
                return

            # Use given points_key if available, else first key
            key = self.points_key if (self.points_key in points_keys) else points_keys[0]
            self.points_key = key
            log(f"Using points key: {key}")

            points_df = self.sdata.points.data[key]
        else:
            log("Unable to find points data structure")
            show_info("Unrecognized points data structure in SpatialData.")
            return

        # Handle dask DataFrame if needed
        if hasattr(points_df, "compute"):
            log("Computing dask DataFrame")
            points_df = points_df.compute()

        self.points_table = points_df
        log(f"Points table shape: {self.points_table.shape}")

        # Check for gene column
        if self.gene_column in self.points_table.columns:
            log(f"Found gene column: {self.gene_column}")
            self.populate_genes()
            if self.gene_selector.count() > 0:
                self.update_transcripts(self.gene_selector.currentText())
        else:
            log(f"Gene column '{self.gene_column}' not found in columns: {list(self.points_table.columns)}")
            show_info(f"Gene column '{self.gene_column}' not found in points table.")

    def set_viewer(self, viewer):
        """
        Set the napari viewer instance.

        Parameters
        ----------
        viewer : napari.Viewer
            The napari viewer instance.

        Examples
        --------
        >>> widget.set_viewer(viewer)
        """
        self.viewer = viewer

    def populate_genes(self):
        """
        Populate the gene selector combobox with unique genes from points table.

        Examples
        --------
        >>> widget.populate_genes()
        >>> print(f"Found {widget.gene_selector.count()} unique genes")
        """
        unique_genes = sorted(self.points_table[self.gene_column].unique())
        self.gene_selector.clear()
        self.gene_selector.addItems([str(g) for g in unique_genes])

    def update_transcripts(self, gene):
        """
        Update transcript list when a gene is selected.

        Parameters
        ----------
        gene : str
            The selected gene.

        Examples
        --------
        >>> widget.update_transcripts("GAPDH")
        """
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
        """
        Add points to the napari viewer as a layer.

        Examples
        --------
        >>> widget._on_add_points_clicked()  # Adds points to viewer
        """
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

    def diagnose(self):
        """
        Run diagnostics to troubleshoot points data issues.

        This function analyzes the current state of the widget and data access,
        providing detailed information about any issues found.

        Examples
        --------
        >>> widget.diagnose()  # Prints diagnostic information
        """

        def log(msg):
            print(msg)
            with open("sdata_debug.txt", "a") as f:
                f.write(msg + "\n")

        log("\n=== DIAGNOSTIC REPORT ===")

        # Check SpatialData
        if self.sdata is None:
            log("❌ SpatialData object is None")
            if self.viewer is not None:
                log("Attempting to retrieve SpatialData from viewer...")
                try:
                    self.sdata = get_sdata_from_viewer(self.viewer)
                    if self.sdata is not None:
                        log("✅ Successfully retrieved SpatialData from viewer")
                        self.set_sdata(self.sdata)
                    else:
                        log("❌ Could not find SpatialData in viewer")
                except Exception as e:
                    log(f"❌ Error retrieving SpatialData: {str(e)}")
            else:
                log("❌ No viewer available to retrieve SpatialData")
        else:
            log("✅ SpatialData object exists")

        # Check points attribute
        if self.sdata is not None:
            if hasattr(self.sdata, "points"):
                log("✅ SpatialData has points attribute")

                # Check points structure
                if hasattr(self.sdata.points, "keys"):
                    points_keys = list(self.sdata.points.keys())
                    log(f"✅ Direct points access available with keys: {points_keys}")
                elif hasattr(self.sdata.points, "data") and hasattr(self.sdata.points.data, "keys"):
                    points_keys = list(self.sdata.points.data.keys())
                    log(f"✅ Nested points access available with keys: {points_keys}")
                else:
                    log(f"❌ Unexpected points structure: {type(self.sdata.points)}")

                # Check points table
                if self.points_table is not None:
                    log(f"✅ Points table exists with {len(self.points_table)} points")
                    log(f"Columns: {list(self.points_table.columns)}")

                    # Check gene column
                    if self.gene_column in self.points_table.columns:
                        unique_genes = self.points_table[self.gene_column].unique()
                        log(f"✅ Gene column '{self.gene_column}' found with {len(unique_genes)} unique genes")
                    else:
                        log(f"❌ Gene column '{self.gene_column}' not found")
                        log(f"Available columns: {list(self.points_table.columns)}")

                        # Suggest potential gene columns
                        potential_columns = [
                            col
                            for col in self.points_table.columns
                            if any(term in col.lower() for term in ["gene", "transcript", "rna", "feature"])
                        ]
                        if potential_columns:
                            log(f"Potential gene columns: {potential_columns}")
                            log("Try setting: widget.gene_column = '<column_name>'")
                else:
                    log("❌ Points table is None")
            else:
                log("❌ SpatialData has no points attribute")

        # Check viewer
        if self.viewer is None:
            log("❌ No napari viewer set")
        else:
            log("✅ Napari viewer is set")

        log("=== END DIAGNOSTIC REPORT ===")


def napari_experimental_provide_dock_widget():
    """
    Provide the GeneTranscriptSelector widget for napari-spatialdata Interactive.

    This function is auto-discovered by napari as an entry point. It tries to find
    a SpatialData object from the Interactive viewer.

    Returns
    -------
    callable
        A factory function that returns the widget.

    Examples
    --------
    >>> import napari
    >>> viewer = napari.Viewer()
    >>> widget = napari_experimental_provide_dock_widget()(viewer)
    """

    def widget_factory(viewer):
        sdata = None
        try:
            sdata = get_sdata_from_viewer(viewer)
            if sdata is None:
                show_info("No SpatialData found. Is this napari-spatialdata Interactive mode?")
        except Exception as e:
            show_info(f"Error finding SpatialData: {str(e)}")
            sdata = None

        widget = GeneTranscriptSelector(sdata)
        widget.set_viewer(viewer)
        return widget

    return widget_factory
