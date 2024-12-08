import React, { useState, useRef, useEffect } from "react";
import { Upload, AlertCircle, FileVideo, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const Home = () => {
    const [video, setVideo] = useState(null);
    const [threshold, setThreshold] = useState(10);
    const [processedVideoUrl, setProcessedVideoUrl] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const videoRef = useRef(null);
    const [file_id, setFileId] = useState(null);
    const [information, setInformation] = useState(null);
    const [csvUrl, setCsvUrl] = useState(null);
    const [dragActive, setDragActive] = useState(false);

    const handleSliderChange = (event) => {
        setThreshold(event.target.value);
    };

    const handleVideoUpload = async (file) => {
        if (file) {
            setVideo(file);
            const formData = new FormData();
            formData.append("file", file);
            try {
                const res = await fetch("http://localhost:8800/api/upload", {
                    method: "POST",
                    body: formData,
                });
                if (!res.ok) throw new Error("Failed to upload video");
                const data = await res.json();
                setFileId(data.file_id);
            } catch (error) {
                console.error(error);
            }
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith("video/")) {
            handleVideoUpload(file);
        }
    };

    const processVideo = async () => {
        if (!video) return;

        setIsProcessing(true);
        try {
            let body = {
                file_id: file_id,
                threshold: threshold,
            };
            const res = await fetch("http://localhost:8800/api/process", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error("Failed to process video");
            const data = await res.json();
            // console.log(data);
            const processedUrl = data.uploaded_files[1].sharing_link;
            const csvUrl = data.uploaded_files[0].sharing_link;
            // console.log(processedUrl);
            setCsvUrl(csvUrl);
            setInformation(data.response);
            setProcessedVideoUrl(processedUrl);
        } catch (error) {
            console.error(error);
        } finally {
            setIsProcessing(false);
        }
    };

    useEffect(() => {
        return () => {
            if (processedVideoUrl) {
                URL.revokeObjectURL(processedVideoUrl);
            }
        };
    }, [processedVideoUrl]);

    return (
        <div className="min-h-screen bg-gray-50 py-12">
            <div className="container mx-auto px-4 max-w-6xl">
                <div className="text-center mb-3">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">
                        Pothole Detection System
                    </h1>
                    <p className="text-gray-600">
                        Upload a video to detect and analyze road conditions
                    </p>
                </div>

                <div className="space-y-0">
                    {/* Upload Section */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileVideo className="w-5 h-5" />
                                Video Upload
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div
                                className={`border-2 border-dashed rounded-lg p-8 text-center ${dragActive
                                    ? "border-blue-500 bg-blue-50"
                                    : "border-gray-300 hover:border-gray-400"
                                    }`}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                            >
                                <input
                                    type="file"
                                    accept="video/*"
                                    onChange={(e) => handleVideoUpload(e.target.files?.[0])}
                                    className="hidden"
                                    id="video-upload"
                                />
                                <label
                                    htmlFor="video-upload"
                                    className="cursor-pointer flex flex-col items-center gap-2"
                                >
                                    <Upload className="w-10 h-4 text-gray-400" />
                                    <span className="text-gray-600">
                                        Drag and drop your video here or click to browse
                                    </span>
                                </label>
                            </div>

                            {video && (
                                <div className="mt-6">
                                    <video
                                        ref={videoRef}
                                        controls
                                        className="w-full rounded-lg shadow-lg"
                                    >
                                        <source src={URL.createObjectURL(video)} type={video.type} />
                                        Your browser does not support the video tag.
                                    </video>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Settings className="w-5 h-5" />
                                Detection Settings
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <label className="block text-lg font-medium text-gray-700">
                                    Critical Zone Threshold: {threshold} potholes
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="20"
                                    value={threshold}
                                    onChange={handleSliderChange}
                                    className="w-full h-2 bg-gray-200 rounded-lg accent-purple-700 cursor-pointer"
                                />
                                <button
                                    onClick={processVideo}
                                    disabled={!video || isProcessing}
                                    className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {isProcessing ? (
                                        <>Processing...</>
                                    ) : (
                                        <>
                                            <AlertCircle className="w-5 h-5" />
                                            Analyze Video
                                        </>
                                    )}
                                </button>
                            </div>
                        </CardContent>
                    </Card>

                    {processedVideoUrl && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Analysis Results</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-6">
                                    <div className="grid grid-cols-2 gap-4">
                                        <a
                                            href={processedVideoUrl}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="flex items-center justify-center gap-2 bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors"
                                        >
                                            <FileVideo className="w-5 h-5 text-blue-600" />
                                            <span className="text-blue-600 font-medium">
                                                View Processed Video
                                            </span>
                                        </a>
                                        <a
                                            href={csvUrl}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="flex items-center justify-center gap-2 bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors"
                                        >
                                            <Upload className="w-5 h-5 text-blue-600" />
                                            <span className="text-blue-600 font-medium">
                                                Download CSV Report
                                            </span>
                                        </a>
                                    </div>

                                    <Alert>
                                        <AlertDescription>
                                            <div className="space-y-2">
                                                <div className="flex items-center">
                                                    <span className="font-bold text-lg">Total Potholes:  </span>
                                                    <span className="text-lg font-bold">
                                                        {information.total_potholes}
                                                    </span>
                                                </div>
                                                <div className="flex items-center">
                                                    <span className="font-bold text-lg">Critical Zones:   </span>
                                                    <span className="text-lg font-bold text-red-600">
                                                        {information.critical_zones.length > 0
                                                            ? information.critical_zones.join(", ")
                                                            : "None"}
                                                    </span>
                                                </div>
                                            </div>
                                        </AlertDescription>
                                    </Alert>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Home;