from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.schemas import GoalCreate, GoalUpdate, GoalOut, GoalStatusEnum
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user

router = APIRouter()


@router.post("/users/{user_id}/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    user_id: int,
    payload: GoalCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    goal = await crud.create_goal(db, user_id, payload.model_dump(exclude_none=True))
    return goal


@router.get("/users/{user_id}/goals", response_model=List[GoalOut])
async def list_goals(
    user_id: int,
    status_filter: Optional[GoalStatusEnum] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    status_val = status_filter.value if status_filter else None
    goals = await crud.list_goals(db, user_id, status=status_val)
    return goals


@router.get("/users/{user_id}/goals/{goal_id}", response_model=GoalOut)
async def get_goal(
    user_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    goal = await crud.get_goal(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/users/{user_id}/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    user_id: int,
    goal_id: int,
    payload: GoalUpdate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    goal = await crud.get_goal(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    updated = await crud.update_goal(db, goal, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/users/{user_id}/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    user_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    goal = await crud.get_goal(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    await crud.delete_goal(db, goal)
