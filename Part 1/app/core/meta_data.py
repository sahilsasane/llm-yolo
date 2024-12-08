import pandas as pd
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime
import logging


class MetadataExtractor:
    """
    A class for extracting comprehensive metadata from pandas DataFrames.
    Provides detailed information about the structure and content of the data.
    """

    def __init__(self, sample_size: int = 5):
        """
        Initialize the MetadataExtractor.
        """
        self.sample_size = sample_size
        self.logger = logging.getLogger(__name__)

    def extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a DataFrame.
        """
        try:
            metadata = {
                "Number of Columns": df.shape[1],
                "Schema": df.columns.tolist(),
                "Data Types": str(df.dtypes),
                "Sample": df.head(1).to_dict(orient="records"),
            }
            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
            return {"error": str(e)}
