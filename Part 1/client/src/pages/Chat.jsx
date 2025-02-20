import React, { useState, useRef } from "react"
import Header from "../components/Header"
import ChatArea from "../components/ChatArea"
import InputArea from "../components/InputArea"
import { useEffect } from "react";


const Chat = () => {
    const [conversation, setConversation] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const socketRef = useRef(null);
    const [fileId, setFileId] = useState("");


    useEffect(() => {
        socketRef.current = new WebSocket("ws://localhost:8800/ws/query");
        socketRef.current.onopen = () => {
            console.log("Connected to WebSocket server");
        };
        socketRef.current.onmessage = (event) => {
            const data = event.data;
            setConversation((prev) =>
                prev.map((message, index) =>
                    index === prev.length - 1 && message.sender === "bot"
                        ? { ...message, message: data }
                        : message
                )
            );
            setIsLoading(false);
        };
        socketRef.current.onclose = () => {
            console.log("Disconnected from WebSocket server");
        }
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
        }
    }, [])

    const handleSendMessage = async (message) => {
        if (!message.trim()) return;
        try {
            if (socketRef.current) {
                const query = { file_id: fileId, query: message };
                socketRef.current.send(JSON.stringify(query));
                setConversation((prev) => [...prev, { conversation_id: 1, message, sender: "You" }]);
                setConversation((prev) => [...prev, { conversation_id: 1, message: "", sender: "bot" }]);
                setIsLoading(true);
            }
        } catch (error) {
            console.error(error);
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen flex-col bg-background overflow-hidden px-28">
            <Header fileid={fileId} setFileid={setFileId} />
            <ChatArea conversation={conversation} loading={isLoading} />
            <InputArea onSendMessage={handleSendMessage} />
        </div>
    )
}

export default Chat