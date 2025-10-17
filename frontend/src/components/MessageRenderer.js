import React from 'react';
import ReactMarkdown from 'react-markdown';
import { AlertCircle, CheckCircle } from 'lucide-react';
import './MessageRenderer.css';

const MessageRenderer = ({ message }) => {
  // Handle user messages
  if (message.type === 'user') {
    return <div className="user-message">{message.content}</div>;
  }

  // Handle bot messages
  const { content, isRelevant, message: errorMessage, isError } = message;

  // Handle error messages
  if (isError) {
    return (
      <div className="error-message">
        <AlertCircle size={16} />
        <span>{content}</span>
      </div>
    );
  }

  // Handle irrelevant queries
  if (isRelevant === false) {
    return (
      <div className="irrelevant-message">
        <AlertCircle size={16} />
        <div>
          <p className="irrelevant-title">Question not related to Sai Sai Kham Leng</p>
          <p className="irrelevant-text">{errorMessage}</p>
        </div>
      </div>
    );
  }

  // Handle regular bot responses with potential structured data
  return (
    <div className="bot-message">
      <CheckCircle size={16} className="success-icon" />
      <div className="message-text">
        <ReactMarkdown
          components={{
            // Custom table rendering
            table: ({ children }) => (
              <div className="table-container">
                <table className="structured-table">{children}</table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="table-header">{children}</thead>
            ),
            tbody: ({ children }) => (
              <tbody className="table-body">{children}</tbody>
            ),
            tr: ({ children }) => (
              <tr className="table-row">{children}</tr>
            ),
            th: ({ children }) => (
              <th className="table-header-cell">{children}</th>
            ),
            td: ({ children }) => (
              <td className="table-cell">{children}</td>
            ),
            // Custom list rendering
            ul: ({ children }) => (
              <ul className="structured-list">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="structured-numbered-list">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="list-item">{children}</li>
            ),
            // Custom paragraph rendering
            p: ({ children }) => (
              <p className="message-paragraph">{children}</p>
            ),
            // Custom strong/bold rendering
            strong: ({ children }) => (
              <strong className="message-bold">{children}</strong>
            ),
            // Custom emphasis/italic rendering
            em: ({ children }) => (
              <em className="message-italic">{children}</em>
            )
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default MessageRenderer;
