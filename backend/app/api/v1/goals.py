from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User
from app.schemas import GoalCreate, GoalUpdate, GoalOut
from app import crud

router = APIRouter()


@router.post("", response_model=GoalOut)
async def create_goal(
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    goal_data = goal_in.dict()
    goal = await crud.create_goal(db, current_user.id, goal_data)
    return goal


@router.get("", response_model=List[GoalOut])
async def list_goals(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    goals = await crud.list_goals(db, current_user.id)
    return goals


@router.get("/progress")
async def get_goal_progress(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    progress = await crud.calculate_goal_progress(db, current_user.id)
    return progress


@router.get("/prediction")
async def get_goal_prediction(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    prediction = await crud.predict_goal_completion(db, current_user.id)
    return prediction


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    goal = await crud.get_goal_by_id(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    goal_in: GoalUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    goal = await crud.get_goal_by_id(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal_data = goal_in.dict(exclude_unset=True)
    updated_goal = await crud.update_goal(db, goal, goal_data)
    return updated_goal


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    success = await crud.delete_goal(db, goal_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted successfully"}
