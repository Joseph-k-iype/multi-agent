import React from 'react';
import { EdgeText, getBezierPath, getSmoothStepPath } from 'reactflow';
import { FaArrowRight, FaSync } from 'react-icons/fa';

const CustomEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style = {},
  markerEnd,
}) => {
  // Determine edge path based on desired style (bezier or step)
  const edgePathType = data?.edgeType || 'bezier';

  // Get path information
  let edgePath = '';
  let pathParams = {};

  if (edgePathType === 'bezier') {
    // For Bezier curves
    [edgePath, pathParams] = getBezierPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
    });
  } else if (edgePathType === 'step') {
    // For step paths (smoother for orthogonal connections)
    [edgePath, pathParams] = getSmoothStepPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
      borderRadius: 8, // optional: rounded corners
    });
  }

  // Define edge colors based on custom properties or default
  const edgeColor = data?.color || style?.stroke || '#555';
  const selectedColor = '#3b82f6'; // Primary color for selected state

  // Prepare edge styles
  const edgeStyles = {
    ...style,
    stroke: edgeColor,
    strokeWidth: style?.strokeWidth || 2,
    strokeDasharray: data?.dashed ? '5,5' : 'none',
  };

  // Calculate position for a floating icon on the edge
  // Positioned at 50% of the path length
  const iconX = (sourceX + targetX) / 2;
  const iconY = (sourceY + targetY) / 2 - 10; // Offset to float above the line

  // Determine the icon based on edge relationship
  const EdgeIcon = data?.loopback ? FaSync : FaArrowRight;

  return (
    <>
      {/* Main edge path */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={edgeStyles}
        markerEnd={markerEnd}
      />
      
      {/* Path for wider hit detection area (invisible) */}
      <path
        id={`${id}-interaction`}
        className="react-flow__edge-interaction-path"
        d={edgePath}
        strokeWidth={15}
        fill="none"
        stroke="transparent"
      />
      
      {/* Edge icon */}
      <foreignObject
        width={20}
        height={20}
        x={iconX - 10}
        y={iconY - 10}
        className="edge-icon-container"
        requiredExtensions="http://www.w3.org/1999/xhtml"
      >
        <div className="edge-floating-icon" style={{ color: edgeColor }}>
          <EdgeIcon size={14} />
        </div>
      </foreignObject>
      
      {/* Edge label */}
      {data?.label && (
        <EdgeText
          x={pathParams.labelX}
          y={pathParams.labelY}
          label={data.label}
          labelStyle={{ fill: edgeColor }}
          labelBgStyle={{ fill: 'white' }}
          labelBgPadding={[2, 4]}
          labelBgBorderRadius={2}
        />
      )}
    </>
  );
};

export default CustomEdge;