"""
DEWAR FBG and Temperature Analysis Module
=========================================

This module provides classes and functions for analyzing Fiber Bragg Grating (FBG)
and temperature data from the DEWAR 1m calibration runs.

Author: DUNE HD Calibration Team
Date: November 2025
"""

import uproot
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class SensorConfig:
    """Configuration for sensor analysis."""
    sensor_indices: List[int] = None  # 0-based indices
    sensor_names: List[str] = None
    colors: List[str] = None
    heights_fbg: Dict[str, float] = None  # Height in meters for FBG sensors
    heights_temp: Dict[str, float] = None  # Height in meters for temperature sensors
    
    def __post_init__(self):
        if self.sensor_indices is None:
            self.sensor_indices = [0, 2, 3, 4]  # Sensors 1, 3, 4, 5
        if self.sensor_names is None:
            self.sensor_names = [f"sensor{i+1}" for i in self.sensor_indices]
        if self.colors is None:
            self.colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]
        if self.heights_fbg is None:
            self.heights_fbg = {
                "sensor1": 2, "sensor2": 3, "sensor3": 4, 
                "sensor4": 5, "sensor5": 6
            }
        if self.heights_temp is None:
            self.heights_temp = {
                "sensor1": 2, "sensor3": 4, 
                "sensor4": 5, "sensor5": 6
            }


class DewarDataLoader:
    """
    Class for loading and preprocessing DEWAR ROOT data files.
    """
    
    def __init__(self, file_path: str, time_correction_hours: float = 2.0):
        """
        Initialize the data loader.
        
        Parameters
        ----------
        file_path : str
            Path to the ROOT file
        time_correction_hours : float
            Time correction to apply to peak timestamps (default: +2 hours)
        """
        self.file_path = file_path
        self.time_correction = datetime.timedelta(hours=time_correction_hours)
        self.peak_data = None
        self.temp_data = None
        self.peak_timestamps = None
        self.temp_timestamps = None
        
    def load_data(self):
        """Load peak and temperature data from ROOT file."""
        with uproot.open(self.file_path) as file:
            peak_tree = file["peak"]
            temp_tree = file["temp"]
            
            self.peak_data = peak_tree.arrays(library="np")
            self.temp_data = temp_tree.arrays(library="np")
        
        # Convert timestamps
        peak_times = self.peak_data["t"][:, 0]
        temp_times = self.temp_data["t"]
        
        self.peak_timestamps = pd.to_datetime(peak_times, unit='s') + self.time_correction
        self.temp_timestamps = pd.to_datetime(temp_times, unit='s')
        
        print(f"✓ Data loaded from: {self.file_path}")
        print(f"  Peak data range: {self.peak_timestamps.min()} → {self.peak_timestamps.max()}")
        print(f"  Temp data range: {self.temp_timestamps.min()} → {self.temp_timestamps.max()}")
        
    def get_sensor_data(self, sensor_idx: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract data for a specific sensor.
        
        Parameters
        ----------
        sensor_idx : int
            0-based sensor index
            
        Returns
        -------
        lambdaB : np.ndarray
            Average Bragg wavelength (meters)
        peak_times : pd.DatetimeIndex
            Peak timestamps
        temperature : np.ndarray
            Temperature values (K)
        temp_times : pd.DatetimeIndex
            Temperature timestamps
        """
        # FBG wavelength (average of two polarizations)
        lambdaB = (self.peak_data["wav"][:, 0, sensor_idx] + 
                   self.peak_data["wav"][:, 1, sensor_idx]) / 2
        
        # Temperature
        temperature = self.temp_data["temp"][:, sensor_idx]
        
        return lambdaB, self.peak_timestamps, temperature, self.temp_timestamps
    
    def filter_time_window(self, start_time: datetime.datetime, 
                          end_time: datetime.datetime) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create boolean masks for time filtering.
        
        Parameters
        ----------
        start_time : datetime
            Start of time window
        end_time : datetime
            End of time window
            
        Returns
        -------
        mask_peak : np.ndarray
            Boolean mask for peak data
        mask_temp : np.ndarray
            Boolean mask for temperature data
        """
        mask_peak = (self.peak_timestamps >= start_time) & (self.peak_timestamps <= end_time)
        mask_temp = (self.temp_timestamps >= start_time) & (self.temp_timestamps <= end_time)
        
        return mask_peak, mask_temp


class DewarAnalyzer:
    """
    Class for analyzing DEWAR FBG and temperature data.
    """
    
    def __init__(self, data_loader: DewarDataLoader, config: SensorConfig = None):
        """
        Initialize the analyzer.
        
        Parameters
        ----------
        data_loader : DewarDataLoader
            Loaded data object
        config : SensorConfig, optional
            Sensor configuration
        """
        self.loader = data_loader
        self.config = config or SensorConfig()
        
    def resample_sensor_data(self, sensor_idx: int, start_time: datetime.datetime,
                            end_time: datetime.datetime, 
                            resample_interval: str = "5min") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Resample sensor data to specified time intervals.
        
        Parameters
        ----------
        sensor_idx : int
            0-based sensor index
        start_time : datetime
            Start of analysis window
        end_time : datetime
            End of analysis window
        resample_interval : str
            Pandas resample string (e.g., "5min", "2min")
            
        Returns
        -------
        peak_resampled : pd.DataFrame
            Resampled peak data with mean and std
        temp_resampled : pd.DataFrame
            Resampled temperature data with mean and std
        """
        # Get data
        lambdaB, peak_times, temperature, temp_times = self.loader.get_sensor_data(sensor_idx)
        
        # Apply time filter
        mask_peak, mask_temp = self.loader.filter_time_window(start_time, end_time)
        
        # Create DataFrames
        df_peak = pd.DataFrame({
            "lambdaB_nm": lambdaB[mask_peak] * 1e9
        }, index=peak_times[mask_peak])
        
        df_temp = pd.DataFrame({
            "temp_K": temperature[mask_temp]
        }, index=temp_times[mask_temp])
        
        # Resample
        peak_resampled = df_peak.resample(resample_interval).agg(['mean', 'std'])
        temp_resampled = df_temp.resample(resample_interval).agg(['mean', 'std'])
        
        # Add standard error
        count_peak = df_peak.resample(resample_interval).count()['lambdaB_nm']
        count_temp = df_temp.resample(resample_interval).count()['temp_K']
        
        peak_resampled['lambdaB_nm', 'se'] = peak_resampled['lambdaB_nm', 'std'] / np.sqrt(count_peak)
        temp_resampled['temp_K', 'se'] = temp_resampled['temp_K', 'std'] / np.sqrt(count_temp)
        
        return peak_resampled, temp_resampled
    
    def fit_temperature_vs_wavelength(self, peak_resampled: pd.DataFrame, 
                                     temp_resampled: pd.DataFrame) -> Dict:
        """
        Perform weighted linear fit of temperature vs wavelength.
        
        Parameters
        ----------
        peak_resampled : pd.DataFrame
            Resampled peak data
        temp_resampled : pd.DataFrame
            Resampled temperature data
            
        Returns
        -------
        fit_results : dict
            Dictionary with slope, intercept, and fit statistics
        """
        df_combined = pd.concat([peak_resampled, temp_resampled], axis=1).dropna()
        
        x = df_combined['lambdaB_nm', 'mean'].values  # nm
        y = df_combined['temp_K', 'mean'].values      # K
        yerr = df_combined['temp_K', 'se'].values
        
        # Weighted linear fit
        w = 1 / yerr**2
        slope, intercept = np.polyfit(x, y, 1, w=w)
        
        # Convert slope to mK/pm
        slope_mK_pm = slope * (1e3 / 1e3)
        
        # Calculate residuals
        y_fit = slope * x + intercept
        residuals = y - y_fit
        
        return {
            'slope_K_nm': slope,
            'slope_mK_pm': slope_mK_pm,
            'intercept_K': intercept,
            'x': x,
            'y': y,
            'yerr': yerr,
            'y_fit': y_fit,
            'residuals': residuals,
            'n_points': len(x)
        }
    
    def compute_sensor_offsets(self, start_time: datetime.datetime, end_time: datetime.datetime,
                              resample_interval: str = "2min", 
                              reference_sensor_idx: int = 4) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compute offsets relative to a reference sensor.
        
        Parameters
        ----------
        start_time : datetime
            Start of analysis window
        end_time : datetime
            End of analysis window
        resample_interval : str
            Resample interval
        reference_sensor_idx : int
            0-based index of reference sensor (default: sensor 5, idx=4)
            
        Returns
        -------
        lambda_offsets_centered : pd.DataFrame
            Centered wavelength offsets (fm)
        temp_offsets_centered : pd.DataFrame
            Centered temperature offsets (mK)
        """
        # Get all sensor data
        sensors_peak = [0, 1, 2, 3, 4]
        sensors_temp = [0, 2, 3, 4]
        
        mask_peak, mask_temp = self.loader.filter_time_window(start_time, end_time)
        
        # Average polarizations
        sensor_lambdaB = np.mean(self.loader.peak_data["wav"][:, :, :], axis=1)
        sensor_temp = self.loader.temp_data["temp"]
        
        # Build DataFrames
        df_peak = pd.DataFrame(
            sensor_lambdaB[mask_peak, :] * 1e15,  # convert to fm
            columns=[f"sensor{i+1}" for i in range(sensor_lambdaB.shape[1])],
            index=self.loader.peak_timestamps[mask_peak]
        )
        
        df_temp = pd.DataFrame(
            sensor_temp[mask_temp, :][:, sensors_temp] * 1e3,  # convert to mK
            columns=[f"sensor{i+1}" for i in sensors_temp],
            index=self.loader.temp_timestamps[mask_temp]
        )
        
        # Resample
        peak_resampled = df_peak.resample(resample_interval).agg(['mean', 'std'])
        temp_resampled = df_temp.resample(resample_interval).agg(['mean', 'std'])
        
        # Compute offsets relative to reference sensor
        ref_sensor_name = f"sensor{reference_sensor_idx+1}"
        
        lambda_mean = peak_resampled.xs('mean', axis=1, level=1)
        lambda_offsets = lambda_mean.subtract(lambda_mean[ref_sensor_name], axis=0)
        lambda_offsets_centered = lambda_offsets - lambda_offsets.mean()
        
        temp_mean = temp_resampled.xs('mean', axis=1, level=1)
        temp_offsets = temp_mean.subtract(temp_mean[ref_sensor_name], axis=0)
        temp_offsets_centered = temp_offsets - temp_offsets.mean()
        
        return lambda_offsets_centered, temp_offsets_centered, peak_resampled, temp_resampled


class DewarPlotter:
    """
    Class for creating plots of DEWAR analysis results.
    """
    
    def __init__(self, config: SensorConfig = None):
        """Initialize the plotter with sensor configuration."""
        self.config = config or SensorConfig()
        plt.style.use("seaborn-v0_8-whitegrid")
    
    def plot_time_series(self, peak_resampled: pd.DataFrame, temp_resampled: pd.DataFrame,
                        sensor_name: str, title_suffix: str = ""):
        """
        Plot wavelength and temperature vs time in two subplots.
        
        Parameters
        ----------
        peak_resampled : pd.DataFrame
            Resampled peak data
        temp_resampled : pd.DataFrame
            Resampled temperature data
        sensor_name : str
            Sensor name for title
        title_suffix : str
            Additional title information
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # λB subplot
        ax1.errorbar(peak_resampled.index, peak_resampled["lambdaB_nm"]["mean"],
                     yerr=peak_resampled["lambdaB_nm"]["std"], fmt='o', color="tab:blue",
                     ecolor='gray', capsize=3, label=f"λB {sensor_name}")
        ax1.set_ylabel("λB (nm)", fontsize=12)
        ax1.set_title(f"{sensor_name}: λB and Temperature vs Time {title_suffix}", fontsize=14)
        ax1.grid(True)
        ax1.legend()
        
        # Temperature subplot
        ax2.errorbar(temp_resampled.index, temp_resampled["temp_K"]["mean"],
                     yerr=temp_resampled["temp_K"]["std"], fmt='o', color="tab:red",
                     ecolor='gray', capsize=3, label=f"Temperature {sensor_name}")
        ax2.set_xlabel("Time (UTC)", fontsize=12)
        ax2.set_ylabel("Temperature (K)", fontsize=12)
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        return fig
    
    def plot_wavelength_vs_temperature(self, fit_results: Dict, sensor_name: str,
                                      title_suffix: str = ""):
        """
        Plot wavelength vs temperature scatter with fit line.
        
        Parameters
        ----------
        fit_results : dict
            Results from fit_temperature_vs_wavelength
        sensor_name : str
            Sensor name for title
        title_suffix : str
            Additional title information
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        x = fit_results['x']
        y = fit_results['y']
        yerr = fit_results['yerr']
        y_fit = fit_results['y_fit']
        slope_mK_pm = fit_results['slope_mK_pm']
        
        ax.errorbar(x, y, yerr=yerr, fmt='o', color='purple', 
                   ecolor='gray', capsize=3, alpha=0.8, label='Data')
        ax.plot(x, y_fit, 'k--', linewidth=2, 
                label=f'Fit: slope = {slope_mK_pm:.2f} mK/pm')
        
        ax.set_xlabel("λB (nm)", fontsize=12)
        ax.set_ylabel("Temperature (K)", fontsize=12)
        ax.set_title(f"{sensor_name}: Temperature vs λB {title_suffix}", fontsize=14)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def plot_multiple_sensors_fit(self, analyzer: 'DewarAnalyzer', 
                                 sensor_indices: List[int],
                                 start_time: datetime.datetime,
                                 end_time: datetime.datetime,
                                 resample_interval: str = "2min"):
        """
        Plot temperature vs wavelength fits for multiple sensors.
        
        Parameters
        ----------
        analyzer : DewarAnalyzer
            Analyzer object with loaded data
        sensor_indices : list
            List of sensor indices to plot
        start_time : datetime
            Start of analysis window
        end_time : datetime
            End of analysis window
        resample_interval : str
            Resample interval
        """
        fig, axes = plt.subplots(len(sensor_indices), 1, figsize=(10, 4*len(sensor_indices)))
        if len(sensor_indices) == 1:
            axes = [axes]
        
        for i, sensor_idx in enumerate(sensor_indices):
            peak_res, temp_res = analyzer.resample_sensor_data(
                sensor_idx, start_time, end_time, resample_interval
            )
            fit_results = analyzer.fit_temperature_vs_wavelength(peak_res, temp_res)
            
            x = fit_results['x']
            y = fit_results['y']
            yerr = fit_results['yerr']
            y_fit = fit_results['y_fit']
            slope_mK_pm = fit_results['slope_mK_pm']
            
            color = self.config.colors[i % len(self.config.colors)]
            sensor_name = f"Sensor {sensor_idx+1}"
            
            axes[i].errorbar(x, y, yerr=yerr, fmt='o', color=color, 
                           ecolor='gray', capsize=3, alpha=0.8, label=sensor_name)
            axes[i].plot(x, y_fit, '-', color=color, linewidth=2,
                        label=f'Fit slope = {slope_mK_pm:.2f} mK/pm')
            
            axes[i].set_xlabel("λB (nm)")
            axes[i].set_ylabel("Temperature (K)")
            axes[i].set_title(f"{sensor_name}: Temperature vs λB")
            axes[i].grid(True)
            axes[i].legend()
        
        plt.tight_layout()
        return fig
    
    def plot_sensor_offsets(self, lambda_offsets: pd.DataFrame, temp_offsets: pd.DataFrame,
                          peak_resampled: pd.DataFrame, temp_resampled: pd.DataFrame,
                          title_suffix: str = ""):
        """
        Plot sensor offsets relative to reference sensor.
        
        Parameters
        ----------
        lambda_offsets : pd.DataFrame
            Wavelength offsets (fm)
        temp_offsets : pd.DataFrame
            Temperature offsets (mK)
        peak_resampled : pd.DataFrame
            Resampled peak data for std
        temp_resampled : pd.DataFrame
            Resampled temp data for std
        title_suffix : str
            Additional title information
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Extract std for error bars
        lambda_std = peak_resampled.xs('std', axis=1, level=1)
        temp_std = temp_resampled.xs('std', axis=1, level=1)
        
        # Compute total std for legend
        lambda_std_total = lambda_offsets.std()
        temp_std_total = temp_offsets.std()
        
        # Plot λB offsets
        for i, sensor_col in enumerate(lambda_offsets.columns):
            if sensor_col in lambda_std.columns:
                color = self.config.colors[i % len(self.config.colors)]
                ax1.errorbar(peak_resampled.index, lambda_offsets[sensor_col],
                           yerr=lambda_std[sensor_col], fmt='o', color=color, 
                           capsize=3, label=f"{sensor_col} (σ={lambda_std_total[sensor_col]:.1f} fm)")
        
        ax1.set_ylabel("λB Offset (fm)", fontsize=12)
        ax1.set_title(f"FBG λB Offsets {title_suffix}", fontsize=14)
        ax1.grid(True)
        ax1.legend()
        
        # Plot temperature offsets
        for i, sensor_col in enumerate(temp_offsets.columns):
            if sensor_col in temp_std.columns:
                # Skip sensor2 in color mapping if needed
                color_idx = i if i < 1 else i + 1
                color = self.config.colors[color_idx % len(self.config.colors)]
                ax2.errorbar(temp_resampled.index, temp_offsets[sensor_col],
                           yerr=temp_std[sensor_col], fmt='o', color=color,
                           capsize=3, label=f"{sensor_col} (σ={temp_std_total[sensor_col]:.1f} mK)")
        
        ax2.set_xlabel("Time (UTC)", fontsize=12)
        ax2.set_ylabel("Temperature Offset (mK)", fontsize=12)
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        return fig


def quick_analysis(file_path: str, date: str, start_hour: int, end_hour: int,
                   sensor_idx: int = 2, resample_interval: str = "5min"):
    """
    Quick analysis function for a single sensor.
    
    Parameters
    ----------
    file_path : str
        Path to ROOT file
    date : str
        Date string (e.g., "2025-11-19")
    start_hour : int
        Start hour (e.g., 16)
    end_hour : int
        End hour (e.g., 18)
    sensor_idx : int
        0-based sensor index (default: 2 for Sensor 3)
    resample_interval : str
        Resample interval (default: "5min")
    """
    # Parse date
    year, month, day = map(int, date.split('-'))
    start_time = datetime.datetime(year, month, day, start_hour, 0, 0)
    end_time = datetime.datetime(year, month, day, end_hour, 0, 0)
    
    # Load data
    loader = DewarDataLoader(file_path)
    loader.load_data()
    
    # Analyze
    analyzer = DewarAnalyzer(loader)
    peak_res, temp_res = analyzer.resample_sensor_data(
        sensor_idx, start_time, end_time, resample_interval
    )
    
    # Fit
    fit_results = analyzer.fit_temperature_vs_wavelength(peak_res, temp_res)
    
    # Plot
    plotter = DewarPlotter()
    sensor_name = f"Sensor {sensor_idx+1}"
    title_suffix = f"({start_hour}:00–{end_hour}:00 {date})"
    
    fig1 = plotter.plot_time_series(peak_res, temp_res, sensor_name, title_suffix)
    plt.show()
    
    fig2 = plotter.plot_wavelength_vs_temperature(fit_results, sensor_name, title_suffix)
    plt.show()
    
    # Print results
    print(f"\n{'='*50}")
    print(f"ANALYSIS RESULTS - {sensor_name}")
    print(f"{'='*50}")
    print(f"Slope: {fit_results['slope_mK_pm']:.2f} mK/pm")
    print(f"Intercept: {fit_results['intercept_K']:.2f} K")
    print(f"Number of points: {fit_results['n_points']}")
    print(f"{'='*50}\n")
    
    return loader, analyzer, plotter, fit_results
